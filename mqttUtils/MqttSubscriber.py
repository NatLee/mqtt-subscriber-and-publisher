"""
MQTT subscriber that prints every message it receives.
"""
from __future__ import annotations

from typing import Any

import paho.mqtt.client as mqtt

from .serialization import loads
from .settings import DEFAULT_PORT


class MqttSubscriber:
    """MQTT subscriber for a list of topics.

    The constructor connects right away. Call ``client.loop_start()`` to
    receive messages on a background thread (or ``client.loop_forever()``
    to block).

    Attributes
    ----------
        host: str
            the MQTT broker host
        topics: list
            the topics (or topic filters such as ``sensors/#``) to subscribe to
        client: paho.mqtt.client.Client
            the underlying paho client
    """

    def __init__(
        self,
        host: str,
        topics: list[str],
        port: int = DEFAULT_PORT,
        *,
        username: str | None = None,
        password: str | None = None,
    ):
        self.host = host
        self.topics = topics
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if username:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message

        self.client.connect(host, port, 60)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Called when the broker answers the CONNECT packet (with CONNACK)."""
        if reason_code.is_failure:
            print(f"Connection refused: {reason_code} (result code {reason_code.value})")
            return
        print(f"Connected with result code {reason_code.value}")

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe([(topic, 0) for topic in self.topics])

    def on_subscribe(self, client, userdata, mid, reason_codes, properties):
        """Called when the broker confirms the subscription (with SUBACK)."""
        print("Subscribed to " + ", ".join(self.topics))

    def on_message(self, client, userdata, msg):
        """Called for every PUBLISH packet the broker forwards to us."""
        try:
            data = self.decode(msg.payload)
        except Exception as error:  # noqa: BLE001 - any bad payload, see below
            # Whoever may publish to the topic decides what arrives, and a
            # broken payload can fail in many ways. Skip it instead of letting
            # the exception stop the background network thread.
            print(f"{msg.topic} <skipped {len(msg.payload)} bytes: {error!r}>")
            return
        print(msg.topic + " " + str(data))

    def decode(self, payload: bytes) -> Any:
        """Turn a payload back into an object; override to use another format."""
        return loads(payload)
