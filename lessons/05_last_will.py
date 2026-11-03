"""Lesson 5: last will and testament."""
from __future__ import annotations

import time
from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, clear_retained, say, step, text

TITLE = "Last will and testament"

STATUS = "lesson05/{sensor}/status"
SENSORS = ["sensor-a", "sensor-b"]
WILL = "offline: connection lost"
GOODBYE = "offline: shut down"
# Seconds between keep-alive pings. The broker gives up on a client that has
# been silent for 1.5 times this long.
KEEPALIVE = 2


@dataclass
class Result:
    timeline: dict[str, list[str]]  # sensor -> status messages the monitor saw, in order
    will_after: float  # seconds from "sensor-b goes silent" to its will arriving
    retained: dict[str, str]  # sensor -> status a late subscriber read


def start_sensor(settings: BrokerSettings, sensor: str) -> Peer:
    peer = Peer(f"lesson05-{sensor}", settings)
    topic = STATUS.format(sensor=sensor)
    # The will is part of CONNECT: the broker stores it and publishes it only
    # if the connection ends without a DISCONNECT packet.
    peer.client.will_set(topic, WILL, qos=1, retain=True)
    peer.connect(keepalive=KEEPALIVE)
    peer.publish(topic, "online", qos=1, retain=True)  # the "birth" message
    return peer


def sensor_of(topic: str) -> str:
    return topic.split("/")[1]


def run(settings: BrokerSettings) -> Result:
    topics = [STATUS.format(sensor=sensor) for sensor in SENSORS]
    monitor = Peer("lesson05-monitor", settings)
    monitor.connect()
    clear_retained(monitor, topics)  # start clean if an earlier run stopped halfway
    monitor.subscribe(STATUS.format(sensor="+"), qos=1)
    timeline: dict[str, list[str]] = {sensor: [] for sensor in SENSORS}

    def heard(message) -> None:
        timeline[sensor_of(message.topic)].append(text(message))
        say(f"monitor: {message.topic} = {text(message)!r}")

    step(1, f"Two sensors connect with a will ({WILL!r}) and say 'online'")
    sensors = {sensor: start_sensor(settings, sensor) for sensor in SENSORS}
    for _ in SENSORS:
        heard(monitor.receive())

    step(2, "sensor-a shuts down politely: it says goodbye itself, then DISCONNECT")
    sensors["sensor-a"].publish(topics[0], GOODBYE, qos=1, retain=True)
    sensors["sensor-a"].disconnect()
    heard(monitor.receive())
    say("a clean DISCONNECT tells the broker to throw the will away")

    step(3, f"sensor-b sends a last reading, then loses power (keep-alive {KEEPALIVE} s)")
    # The broker times the silence from the last packet it got from sensor-b,
    # so send one right before going quiet to start the clock now.
    sensors["sensor-b"].publish("lesson05/sensor-b/temperature", "21.0 C", qos=1)
    sensors["sensor-b"].go_silent()
    silent_since = time.monotonic()
    say("no DISCONNECT, and no more PINGREQ keep-alives either")
    message = monitor.receive(timeout=KEEPALIVE * 1.5 + 5)
    will_after = time.monotonic() - silent_since
    heard(message)
    say(f"the broker published the will {will_after:.1f} s later "
        f"(1.5 x keep-alive = {KEEPALIVE * 1.5:g} s, timed by a clock that ticks in whole seconds)")
    # The broker has closed sensor-b's connection; release our end of it.
    sensors["sensor-b"].client.disconnect()

    for message in monitor.receive_rest():  # a will from sensor-a would show up here
        heard(message)
    monitor.disconnect()

    step(4, "A dashboard that starts now reads the retained statuses")
    dashboard = Peer("lesson05-dashboard", settings)
    dashboard.connect()
    dashboard.subscribe(STATUS.format(sensor="+"), qos=1)
    retained = {sensor_of(m.topic): text(m) for m in dashboard.receive_rest()}
    for sensor in SENSORS:
        say(f"{sensor}: {retained.get(sensor)!r}")
    clear_retained(dashboard, topics)
    dashboard.disconnect()

    check(
        timeline == {"sensor-a": ["online", GOODBYE], "sensor-b": ["online", WILL]},
        "only the sensor that vanished got its will published",
    )
    return Result(timeline, will_after, retained)
