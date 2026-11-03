"""
Shared plumbing for the lessons, so each lesson file shows only the MQTT idea.

Everything MQTT-related still goes through the normal paho-mqtt API: a Peer is
a paho ``Client`` plus a mailbox of received messages, an optional packet
trace, and helpers that *wait* for the broker's answer so the lesson code can
read top to bottom like a story.
"""
from __future__ import annotations

import os
import queue
import re
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.subscribeoptions import SubscribeOptions

from mqttUtils import BrokerSettings

# The demo account; compose.yaml passes the same file to the broker.
COURSE_ENV = Path(__file__).resolve().parent.parent / "course.env"

# How long to wait for something the broker should do right away.
TIMEOUT = 5.0
# How long to listen before concluding that "nothing else is coming".
QUIET = 0.5

Payload = str | bytes | None


# --------------------------------------------------------------------------
# Settings


def course_settings(environ: Mapping[str, str] = os.environ) -> BrokerSettings:
    """MQTT_* environment variables win; course.env fills in the demo account.

    Inside the course containers compose sets everything. On your own machine
    the defaults reach the broker that ``docker compose up -d broker`` publishes
    on localhost:1883.
    """
    return BrokerSettings.from_env(environ, defaults_file=COURSE_ENV)


# --------------------------------------------------------------------------
# Errors with a hint on what to do next


class LessonError(Exception):
    """Something the learner can fix; the message says how."""


class BrokerUnreachable(LessonError):
    pass


class ConnectionRefused(LessonError):
    """The broker answered CONNECT with a failure reason code."""

    def __init__(self, peer: str, reason: ReasonCode):
        super().__init__(f"{peer}: the broker refused the connection: {reason} (code {reason.value})")
        self.reason = reason


class NothingArrived(LessonError):
    pass


# --------------------------------------------------------------------------
# Packet trace


@dataclass(frozen=True)
class Packet:
    """One MQTT control packet as the client saw it."""

    sent: bool  # True: client -> broker, False: broker -> client
    kind: str  # PUBLISH, PUBACK, PUBREC, ...
    qos: int | None = None  # PUBLISH only
    dup: bool | None = None  # PUBLISH only
    mid: int | None = None  # packet identifier, when the packet has one

    def __str__(self) -> str:
        arrow = ">>" if self.sent else "<<"
        details = []
        if self.qos is not None:
            details.append(f"qos {self.qos}")
        if self.dup:
            details.append("dup")
        if self.mid:
            details.append(f"id {self.mid}")
        return f"{arrow} {self.kind}" + (f" ({', '.join(details)})" if details else "")


# paho-mqtt reports every packet it sends or receives through the public
# on_log callback, e.g. "Sending PUBLISH (d0, q1, r0, m1), 'b'topic'', ...".
# The wording is not a formal API, so it is parsed here and nowhere else, and
# tests/test_03_qos.py fails loudly if a paho release changes it.
_PACKET_LOG = re.compile(r"^(Sending|Received) ([A-Z]+)\b(.*)$")
_PUBLISH_FLAGS = re.compile(r"\(d(\d), q(\d), r\d, m(\d+)\)")
_MID = re.compile(r"Mid: (\d+)")


def parse_packet_log(line: str) -> Packet | None:
    match = _PACKET_LOG.match(line)
    if not match:
        return None
    direction, kind, rest = match.groups()
    sent = direction == "Sending"
    flags = _PUBLISH_FLAGS.search(rest) if kind == "PUBLISH" else None
    if flags:
        dup, qos, mid = (int(value) for value in flags.groups())
        # QoS 0 PUBLISH packets carry no packet identifier on the wire; the
        # number paho logs for them is only its own counter.
        return Packet(sent, kind, qos=qos, dup=bool(dup), mid=mid if qos else None)
    mid_match = _MID.search(rest)
    return Packet(sent, kind, mid=int(mid_match.group(1)) if mid_match else None)


# --------------------------------------------------------------------------
# A client in a lesson


@dataclass(frozen=True)
class ConnAck:
    """What the broker said in CONNACK."""

    reason: ReasonCode
    session_present: bool
    properties: Properties | None


class Peer:
    """One MQTT client in a lesson, e.g. Peer("lesson04-display", settings).

    ``peer.client`` is the paho Client; use it directly for anything the
    helpers below don't cover.
    """

    def __init__(
        self,
        name: str,
        settings: BrokerSettings,
        *,
        trace: bool = False,
        manual_ack: bool = False,
        login: bool = True,
        password: str | None = None,
    ):
        self.name = name
        self.settings = settings
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=name,
            protocol=mqtt.MQTTv5,
            manual_ack=manual_ack,
        )
        if login and settings.username:
            self.client.username_pw_set(settings.username, password or settings.password)
        self.inbox: queue.Queue[mqtt.MQTTMessage] = queue.Queue()
        self.packets: list[Packet] = []
        self._connacks: queue.Queue[ConnAck] = queue.Queue()
        self._subacks: queue.Queue[tuple[int, list[ReasonCode]]] = queue.Queue()
        self._lock = threading.Lock()
        self.client.on_connect = self._on_connect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message
        if trace:
            self.client.on_log = self._on_log

    # -- paho callbacks (they run on paho's network thread) -----------------

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self._connacks.put(ConnAck(reason_code, flags.session_present, properties))

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        self._subacks.put((mid, list(reason_codes)))

    def _on_message(self, client, userdata, message):
        self.inbox.put(message)

    def _on_log(self, client, userdata, level, line):
        packet = parse_packet_log(line)
        if packet and packet.kind not in ("PINGREQ", "PINGRESP"):
            with self._lock:
                self.packets.append(packet)

    # -- connecting ---------------------------------------------------------

    def connect(
        self,
        *,
        clean_start: bool = True,
        session_expiry: int | None = None,
        keepalive: int = 60,
    ) -> ConnAck:
        """Send CONNECT and wait for CONNACK. Raises ConnectionRefused on failure.

        ``session_expiry`` (seconds) asks the broker to keep the session after
        we disconnect; None means the session ends with the connection.
        """
        properties = None
        if session_expiry is not None:
            properties = Properties(PacketTypes.CONNECT)
            properties.SessionExpiryInterval = session_expiry
        try:
            self.client.connect(
                self.settings.host,
                self.settings.port,
                keepalive=keepalive,
                clean_start=clean_start,
                properties=properties,
            )
        except OSError as error:  # refused, unknown host, timeout, ...
            raise BrokerUnreachable(self.settings.unreachable(error)) from error
        self.client.loop_start()
        try:
            connack = self._connacks.get(timeout=TIMEOUT)
        except queue.Empty:
            self.client.loop_stop()
            raise NothingArrived(f"{self.name}: no CONNACK within {TIMEOUT} s") from None
        if connack.reason.is_failure:
            # Stop here, or paho's network thread would keep retrying.
            self.client.loop_stop()
            self.client.disconnect()
            raise ConnectionRefused(self.name, connack.reason)
        return connack

    def disconnect(self) -> None:
        """Say goodbye politely (DISCONNECT) and stop the network thread."""
        self.client.disconnect()
        self.client.loop_stop()

    def go_silent(self) -> None:
        """Stop talking without saying goodbye, like a device that lost power.

        The network thread stops, so no more PINGREQ keep-alives go out, but no
        DISCONNECT is sent either. The broker only notices once the keep-alive
        time runs out.
        """
        self.client.loop_stop()

    # -- subscribing and publishing ----------------------------------------

    def subscribe(
        self,
        topic: str,
        qos: int = 0,
        *,
        properties: Properties | None = None,
        **options: object,
    ) -> list[ReasonCode]:
        """Send SUBSCRIBE and wait for SUBACK; returns the granted reason codes.

        Extra keyword arguments become MQTT 5 subscribe options, e.g.
        ``retainHandling=2`` (see paho.mqtt.subscribeoptions.SubscribeOptions).
        """
        result, mid = self.client.subscribe(
            topic, options=SubscribeOptions(qos=qos, **options), properties=properties
        )
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise LessonError(f"{self.name}: subscribe failed: {mqtt.error_string(result)}")
        deadline = time.monotonic() + TIMEOUT
        while time.monotonic() < deadline:
            try:
                acked_mid, reason_codes = self._subacks.get(timeout=deadline - time.monotonic())
            except queue.Empty:
                break
            if acked_mid == mid:
                return reason_codes
        raise NothingArrived(f"{self.name}: no SUBACK for {topic!r} within {TIMEOUT} s")

    def publish(
        self,
        topic: str,
        payload: Payload,
        qos: int = 0,
        *,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> mqtt.MQTTMessageInfo:
        """Publish and wait until paho has finished its side of the QoS handshake."""
        info = self.client.publish(topic, payload, qos=qos, retain=retain, properties=properties)
        info.wait_for_publish(timeout=TIMEOUT)
        if not info.is_published():
            raise NothingArrived(f"{self.name}: publish to {topic!r} did not complete")
        return info

    # -- receiving ----------------------------------------------------------

    def receive(self, timeout: float = TIMEOUT) -> mqtt.MQTTMessage:
        """Wait for the next message."""
        try:
            return self.inbox.get(timeout=timeout)
        except queue.Empty:
            raise NothingArrived(f"{self.name}: no message within {timeout} s") from None

    def receive_rest(self, quiet: float = QUIET) -> list[mqtt.MQTTMessage]:
        """Collect messages until none arrives for ``quiet`` seconds."""
        messages = []
        while True:
            try:
                messages.append(self.inbox.get(timeout=quiet))
            except queue.Empty:
                return messages

    def wait_for_packets(self, count: int, timeout: float = TIMEOUT) -> list[Packet]:
        """Wait until the trace holds ``count`` packets, then return a copy."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if len(self.packets) >= count:
                    return list(self.packets)
            time.sleep(0.01)
        with self._lock:
            return list(self.packets)

    def clear_trace(self) -> None:
        with self._lock:
            self.packets.clear()


# --------------------------------------------------------------------------
# Small helpers


def text(message: mqtt.MQTTMessage) -> str:
    """The payload as text (all lesson payloads are UTF-8)."""
    return message.payload.decode("utf-8")


def publish_properties(**values: object) -> Properties:
    """Build PUBLISH properties, e.g. publish_properties(MessageExpiryInterval=5)."""
    properties = Properties(PacketTypes.PUBLISH)
    for name, value in values.items():
        setattr(properties, name, value)
    return properties


def clear_retained(peer: Peer, topics: Sequence[str]) -> None:
    """Delete retained messages: an empty retained payload removes them."""
    for topic in topics:
        peer.publish(topic, None, qos=1, retain=True)


def say(line: str = "", indent: int = 1) -> None:
    print("   " * indent + line if line else "")


def step(number: int, title: str) -> None:
    print(f"\n{number}. {title}")


def check(condition: bool, line: str) -> None:
    """Print a result line, marked [ok] or [!!] so surprises stand out."""
    say(f"{'[ok]' if condition else '[!!]'} {line}")

