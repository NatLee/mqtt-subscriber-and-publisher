"""Lesson 3: QoS 0, 1 and 2."""
from __future__ import annotations

from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Packet, Peer, check, say, step, text

TITLE = "QoS 0, 1 and 2"

ROOT = "lesson03"

# What each QoS level promises, and the packets that keep the promise on
# every hop (publisher <-> broker, then broker <-> subscriber).
LEVELS = {
    0: ("at most once", ["PUBLISH"]),
    1: ("at least once", ["PUBLISH", "PUBACK"]),
    2: ("exactly once", ["PUBLISH", "PUBREC", "PUBREL", "PUBCOMP"]),
}


@dataclass
class Result:
    # qos -> (packets the publisher saw, packets the subscriber saw)
    handshakes: dict[int, tuple[list[Packet], list[Packet]]]
    granted_qos: int  # what the broker granted a QoS 0 subscription
    delivered_qos: int  # QoS of a QoS 2 message delivered on that subscription
    dup_flags: list[bool]  # DUP flag of each delivery of one unacknowledged QoS 1 message


def show_leg(label: str, packets: list[Packet]) -> None:
    say(f"{label:<24}" + "   ".join(str(packet) for packet in packets))


def handshakes(settings: BrokerSettings) -> dict[int, tuple[list[Packet], list[Packet]]]:
    topic = f"{ROOT}/handshake"
    subscriber = Peer("lesson03-subscriber", settings, trace=True)
    subscriber.connect()
    subscriber.subscribe(topic, qos=2)  # accept up to QoS 2
    publisher = Peer("lesson03-publisher", settings, trace=True)
    publisher.connect()

    seen = {}
    for qos, (promise, expected) in LEVELS.items():
        step(qos + 1, f"QoS {qos}: {promise}")
        publisher.clear_trace()
        subscriber.clear_trace()
        publisher.publish(topic, f"reading #{qos + 1}", qos=qos)
        message = subscriber.receive()
        legs = (
            publisher.wait_for_packets(len(expected)),
            subscriber.wait_for_packets(len(expected)),
        )
        show_leg("publisher <-> broker", legs[0])
        show_leg("broker <-> subscriber", legs[1])
        check(message.qos == qos, f"subscriber got {text(message)!r} with QoS {message.qos}")
        seen[qos] = legs

    publisher.disconnect()
    subscriber.disconnect()
    return seen


def downgrade(settings: BrokerSettings) -> tuple[int, int]:
    step(4, "The subscriber has a say too: delivered QoS = min(publish QoS, subscription QoS)")
    topic = f"{ROOT}/downgrade"
    listener = Peer("lesson03-qos0-listener", settings)
    listener.connect()
    granted = listener.subscribe(topic, qos=0)[0].value
    say(f"listener subscribed with QoS 0, SUBACK granted QoS {granted}")
    publisher = Peer("lesson03-publisher", settings)
    publisher.connect()
    publisher.publish(topic, "important", qos=2)
    publisher.disconnect()
    message = listener.receive()
    listener.disconnect()
    check(message.qos == 0, f"published with QoS 2, delivered with QoS {message.qos}")
    return granted, message.qos


def redelivery(settings: BrokerSettings) -> list[bool]:
    step(5, "At least once can mean twice: an unacknowledged QoS 1 message comes back")
    topic = f"{ROOT}/orders"
    name = "lesson03-worker"
    # manual_ack: paho waits for us to call client.ack() instead of sending
    # PUBACK by itself. We "crash" before acknowledging.
    worker = Peer(name, settings, manual_ack=True)
    worker.connect(clean_start=True, session_expiry=60)  # keep the session for 60 s
    worker.subscribe(topic, qos=1)
    shop = Peer("lesson03-shop", settings)
    shop.connect()
    shop.publish(topic, "order #1", qos=1)
    shop.disconnect()
    first = worker.receive()
    say(f"worker got {text(first)!r} (dup={first.dup}) and goes away without a PUBACK")
    worker.disconnect()

    restarted = Peer(name, settings)  # same client id, acknowledges normally
    connack = restarted.connect(clean_start=False, session_expiry=0)  # resume, then end it
    second = restarted.receive()
    say(f"worker is back (session present: {connack.session_present}), "
        f"got {text(second)!r} again (dup={second.dup})")
    restarted.disconnect()
    check(text(first) == text(second), "same message delivered twice: make handlers idempotent")
    return [first.dup, second.dup]


def run(settings: BrokerSettings) -> Result:
    seen = handshakes(settings)
    granted, delivered = downgrade(settings)
    dup_flags = redelivery(settings)
    return Result(seen, granted, delivered, dup_flags)
