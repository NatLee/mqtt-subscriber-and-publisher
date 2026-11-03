"""Lesson 10: MQTT 5 request / response."""
from __future__ import annotations

import json
from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, publish_properties, say, step, text

TITLE = "MQTT 5: request / response"

REQUESTS = "lesson10/requests/sum"
APP = "lesson10-app"
RESPONSES = f"lesson10/responses/{APP}"  # a reply topic only this app reads
QUESTIONS = {"req-1": [1, 2, 3], "req-2": [10, 20], "req-3": [7]}


@dataclass
class Result:
    answers: dict[str, int]  # correlation id -> answer the app received
    expected: dict[str, int]


def start_calculator(settings: BrokerSettings) -> Peer:
    service = Peer("lesson10-calculator", settings)

    def answer(client, userdata, message) -> None:
        # Runs on paho's network thread: publish, but don't wait here.
        reply_to = message.properties.ResponseTopic
        properties = publish_properties(CorrelationData=message.properties.CorrelationData)
        total = sum(json.loads(text(message)))
        client.publish(reply_to, json.dumps(total), qos=1, properties=properties)

    # message_callback_add routes one topic filter to its own handler.
    service.client.message_callback_add(REQUESTS, answer)
    service.connect()
    service.subscribe(REQUESTS, qos=1)
    return service


def run(settings: BrokerSettings) -> Result:
    step(1, "A calculator service listens for requests")
    calculator = start_calculator(settings)
    say(f"calculator subscribes to {REQUESTS}")

    step(2, "The app subscribes to its own reply topic, then sends three requests")
    app = Peer(APP, settings)
    app.connect()
    app.subscribe(RESPONSES, qos=1)
    for correlation, numbers in QUESTIONS.items():
        properties = publish_properties(
            ResponseTopic=RESPONSES,  # "send the answer here"
            CorrelationData=correlation.encode(),  # "and quote this so I can match it"
        )
        app.publish(REQUESTS, json.dumps(numbers), qos=1, properties=properties)
        say(f"app -> {REQUESTS}: sum{numbers}  (correlation {correlation})")

    step(3, "Answers come back on the reply topic; correlation data pairs them up")
    answers = {}
    for _ in QUESTIONS:
        message = app.receive()
        correlation = message.properties.CorrelationData.decode()
        answers[correlation] = json.loads(text(message))
        say(f"app <- {message.topic}: {answers[correlation]}  (correlation {correlation})")
    app.disconnect()
    calculator.disconnect()

    expected = {correlation: sum(numbers) for correlation, numbers in QUESTIONS.items()}
    check(answers == expected, "every answer matched the request it belongs to")
    return Result(answers, expected)
