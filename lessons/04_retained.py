"""Lesson 4: retained messages."""
from __future__ import annotations

from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, clear_retained, say, step, text

TITLE = "Retained messages"

TOPIC = "lesson04/livingroom/temperature"


@dataclass
class Result:
    first_join: tuple[str, bool]  # (payload, retain flag) a new subscriber got at once
    live: tuple[str, bool]  # an update that arrived while subscribed
    second_join: tuple[str, bool]  # what the next new subscriber got
    after_clear: list[str]  # what a subscriber got after the retained message was deleted


def join(settings: BrokerSettings, name: str) -> Peer:
    peer = Peer(name, settings)
    peer.connect()
    peer.subscribe(TOPIC, qos=1)
    return peer


def run(settings: BrokerSettings) -> Result:
    thermostat = Peer("lesson04-thermostat", settings)
    thermostat.connect()
    clear_retained(thermostat, [TOPIC])  # start clean if an earlier run stopped halfway

    step(1, "The thermostat publishes 21.5 C with the retain flag, nobody is listening")
    thermostat.publish(TOPIC, "21.5 C", qos=1, retain=True)
    say("the broker keeps the last retained message of each topic")

    step(2, "A display subscribes later and gets the value at once")
    display = join(settings, "lesson04-display")
    message = display.receive()
    first = (text(message), message.retain)
    check(message.retain, f"display got {first[0]!r} with retain={message.retain} (stored value)")

    step(3, "A live update reaches current subscribers with retain=False")
    thermostat.publish(TOPIC, "21.7 C", qos=1, retain=True)
    message = display.receive()
    live = (text(message), message.retain)
    check(not message.retain, f"display got {live[0]!r} with retain={message.retain} (live)")

    step(4, "A phone joins: only the latest retained value is kept")
    phone = join(settings, "lesson04-phone")
    message = phone.receive()
    second = (text(message), message.retain)
    check(second[0] == "21.7 C", f"phone got {second[0]!r} with retain={message.retain}")
    for peer in (display, phone):
        peer.disconnect()

    step(5, "Delete the retained value by publishing an empty retained message")
    clear_retained(thermostat, [TOPIC])
    thermostat.disconnect()
    tablet = join(settings, "lesson04-tablet")
    after_clear = [text(m) for m in tablet.receive_rest()]
    tablet.disconnect()
    check(not after_clear, f"tablet joined and got {len(after_clear)} messages")

    return Result(first, live, second, after_clear)
