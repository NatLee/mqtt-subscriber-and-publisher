"""Lesson 7: MQTT 5 user properties and content type."""
from __future__ import annotations

import json
from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, publish_properties, say, step, text

TITLE = "MQTT 5: user properties"

TOPIC = "lesson07/greenhouse/climate"
READING = {"temperature": 24.5, "humidity": 61}
# Like HTTP headers: free-form (name, value) pairs. Order is kept and a name
# may appear more than once.
USER_PROPERTIES = [
    ("sensor-id", "gh-07"),
    ("firmware", "1.4.2"),
    ("calibrated-by", "alice"),
    ("calibrated-by", "bob"),
]
CONTENT_TYPE = "application/json"


@dataclass
class Result:
    reading: dict
    content_type: str | None
    payload_is_utf8: bool
    user_properties: list[tuple[str, str]]


def run(settings: BrokerSettings) -> Result:
    step(1, "A dashboard subscribes")
    dashboard = Peer("lesson07-dashboard", settings)
    dashboard.connect()
    dashboard.subscribe(TOPIC, qos=1)
    say(f"dashboard: subscribed to {TOPIC}")

    step(2, "The sensor publishes JSON, and describes it in properties")
    properties = publish_properties(
        ContentType=CONTENT_TYPE,  # what the payload is
        PayloadFormatIndicator=1,  # 1 = UTF-8 text, 0 = raw bytes
        UserProperty=USER_PROPERTIES,  # anything else you want to say
    )
    sensor = Peer("lesson07-sensor", settings)
    sensor.connect()
    sensor.publish(TOPIC, json.dumps(READING), qos=1, properties=properties)
    sensor.disconnect()
    say(f"payload: {json.dumps(READING)}")
    for name, value in USER_PROPERTIES:
        say(f"user property {name} = {value}")

    step(3, "The dashboard reads the properties before touching the payload")
    message = dashboard.receive()
    dashboard.disconnect()
    received = message.properties
    content_type = getattr(received, "ContentType", None)
    is_utf8 = getattr(received, "PayloadFormatIndicator", 0) == 1
    user_properties = [tuple(pair) for pair in getattr(received, "UserProperty", [])]
    say(f"content type: {content_type}, UTF-8 text: {is_utf8}")
    say(f"user properties: {user_properties}")
    reading = json.loads(text(message)) if content_type == CONTENT_TYPE else {}
    check(reading == READING, f"decoded the JSON reading: {reading}")

    return Result(reading, content_type, is_utf8, user_properties)
