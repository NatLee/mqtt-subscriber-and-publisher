"""Lesson 2: topics and wildcards."""
from __future__ import annotations

from dataclasses import dataclass

import paho.mqtt.client as mqtt

from mqttUtils import BrokerSettings

from ._kit import Peer, check, say, step

TITLE = "Topics and wildcards"

ROOT = "lesson02"

# Topics are just strings; "/" splits them into levels. Nothing has to be
# created first: publishing to a topic is enough for it to exist.
TOPICS = [
    "home",
    "home/kitchen/temperature",
    "home/kitchen/humidity",
    "home/garage/temperature",
    "home/garage/door/state",
    "office/kitchen/temperature",
]

# "+" matches exactly one level, "#" matches this level and everything below.
FILTERS = [
    "home/kitchen/temperature",
    "home/+/temperature",
    "home/#",
    "+/kitchen/#",
    "+/+/temperature",
]


@dataclass
class Result:
    received: dict[str, list[str]]  # filter -> topics its subscriber got
    expected: dict[str, list[str]]  # filter -> topics paho's matcher predicts


def run(settings: BrokerSettings) -> Result:
    step(1, "Subscribe with five topic filters, one client each")
    say(f"(every topic in this lesson starts with {ROOT}/, left out below)")
    listeners = {}
    for index, topic_filter in enumerate(FILTERS, start=1):
        listener = Peer(f"lesson02-listener-{index}", settings)
        listener.connect()
        listener.subscribe(f"{ROOT}/{topic_filter}")
        listeners[topic_filter] = listener
        say(f"listener {index}: {topic_filter}")

    step(2, f"Publish one message to each of {len(TOPICS)} topics")
    sensor = Peer("lesson02-sensor", settings)
    sensor.connect()
    for topic in TOPICS:
        sensor.publish(f"{ROOT}/{topic}", f"hello from {topic}", qos=1)
        say(f"-> {topic}")
    sensor.disconnect()

    step(3, "Which listener heard what")
    received = {}
    expected = {}
    for topic_filter, listener in listeners.items():
        got = [message.topic[len(ROOT) + 1 :] for message in listener.receive_rest()]
        listener.disconnect()
        received[topic_filter] = got
        # paho's own matcher, to double-check the broker
        expected[topic_filter] = [t for t in TOPICS if mqtt.topic_matches_sub(topic_filter, t)]
        say(f"{topic_filter:<26} heard {len(got)}: {', '.join(got) or '-'}")

    say()
    check(received == expected, "the broker matched exactly what paho.mqtt.client.topic_matches_sub predicts")
    return Result(received, expected)
