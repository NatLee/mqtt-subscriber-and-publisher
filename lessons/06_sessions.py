"""Lesson 6: clean and persistent sessions."""
from __future__ import annotations

from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, say, step, text

TITLE = "Clean and persistent sessions"

TOPIC = "lesson06/alerts"
PHONE = "lesson06-phone"
# How long the broker keeps a session after the client disconnects.
SESSION_EXPIRY = 300


@dataclass
class Result:
    first_session_present: bool  # very first connect
    resumed_session_present: bool  # reconnect with clean_start=False
    resumed_messages: list[str]  # delivered after resuming
    clean_session_present: bool  # reconnect with clean_start=True
    clean_messages: list[str]  # delivered after starting clean


def send_alerts(settings: BrokerSettings, alerts: list[tuple[str, int]]) -> None:
    server = Peer("lesson06-server", settings)
    server.connect()
    for payload, qos in alerts:
        server.publish(TOPIC, payload, qos=qos)
        say(f"server -> {TOPIC}: {payload!r}")
    server.disconnect()


def run(settings: BrokerSettings) -> Result:
    step(1, f"The phone connects, asks the broker to keep its session for {SESSION_EXPIRY} s, subscribes")
    phone = Peer(PHONE, settings)
    connack = phone.connect(clean_start=True, session_expiry=SESSION_EXPIRY)
    first_present = connack.session_present
    say(f"CONNACK session present: {first_present}")
    phone.subscribe(TOPIC, qos=1)
    phone.disconnect()
    say("phone goes offline (tunnel, flight mode, ...)")

    step(2, "Alerts are sent while the phone is offline")
    send_alerts(settings, [("alert 1 (QoS 0)", 0), ("alert 2 (QoS 1)", 1)])

    step(3, "The phone comes back with clean_start=False: resume the old session")
    phone = Peer(PHONE, settings)
    connack = phone.connect(clean_start=False, session_expiry=SESSION_EXPIRY)
    resumed_present = connack.session_present
    resumed = [text(m) for m in phone.receive_rest()]
    say(f"CONNACK session present: {resumed_present}  (no need to subscribe again)")
    say(f"queued for the phone: {resumed}")
    check(resumed == ["alert 2 (QoS 1)"], "QoS 1 waited for the phone, QoS 0 was not queued")
    phone.disconnect()

    step(4, "Another alert, then the phone reconnects with clean_start=True")
    send_alerts(settings, [("alert 3 (QoS 1)", 1)])
    phone = Peer(PHONE, settings)
    # session_expiry=None: this session ends when the connection does.
    connack = phone.connect(clean_start=True)
    clean_present = connack.session_present
    clean = [text(m) for m in phone.receive_rest()]
    phone.disconnect()
    say(f"CONNACK session present: {clean_present}")
    check(not clean, f"a clean start threw away the queue and the subscription: got {clean}")

    return Result(first_present, resumed_present, resumed, clean_present, clean)
