"""
Send Python objects to one MQTT topic.
"""
from __future__ import annotations

from typing import Any

import paho.mqtt.publish as publish

from .serialization import dumps
from .settings import DEFAULT_PORT


class MqttSender:
    """MQTT sender bound to one topic.

    Attributes
    ----------
        topic: str
            the topic every message goes to
        hostname: str
            the MQTT broker host
        port: int
            the MQTT broker port

    Methods
    ----------
        send(data)
            pickle ``data`` and publish it to ``topic``
    """

    def __init__(
        self,
        topic: str,
        hostname: str,
        port: int = DEFAULT_PORT,
        *,
        username: str | None = None,
        password: str | None = None,
    ):
        self.topic = topic
        self.hostname = hostname
        self.port = port
        self.auth = {"username": username, "password": password} if username else None

    def send(self, data: Any) -> bool:
        """Publish ``data`` (any picklable object) and return True once it is sent.

        Each call opens a connection, publishes with QoS 0 and disconnects:
        simple, but slow for many messages. The lessons show how to keep one
        connection open instead.
        """
        publish.single(
            self.topic, payload=dumps(data), hostname=self.hostname, port=self.port, auth=self.auth
        )
        return True
