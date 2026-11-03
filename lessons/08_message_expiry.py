"""Lesson 8: MQTT 5 message expiry."""
from __future__ import annotations

import time
from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, clear_retained, publish_properties, say, step, text

TITLE = "MQTT 5: message expiry"

ROOT = "lesson08/offers"
# topic -> (payload, seconds the message stays valid; None = forever)
OFFERS = {
    f"{ROOT}/flash-sale": ("50% off, today only", 2),
    f"{ROOT}/weekly-menu": ("soup of the week: pumpkin", 3600),
    f"{ROOT}/opening-hours": ("9:00-18:00", None),
}
WAIT = 3  # seconds: longer than the flash sale lives


@dataclass
class Result:
    # topic -> remaining expiry the broker reported (None = never expires),
    # for every retained message a late subscriber still got
    delivered: dict[str, int | None]


def run(settings: BrokerSettings) -> Result:
    shop = Peer("lesson08-shop", settings)
    shop.connect()
    clear_retained(shop, OFFERS)  # start clean if an earlier run stopped halfway

    step(1, "The shop publishes three retained offers, each with its own lifetime")
    for topic, (payload, expiry) in OFFERS.items():
        properties = publish_properties(MessageExpiryInterval=expiry) if expiry else None
        shop.publish(topic, payload, qos=1, retain=True, properties=properties)
        lifetime = f"expires after {expiry} s" if expiry else "never expires"
        say(f"{topic}: {payload!r}, {lifetime}")

    step(2, f"A customer opens the app {WAIT} s later")
    time.sleep(WAIT)
    customer = Peer("lesson08-customer", settings)
    customer.connect()
    customer.subscribe(f"{ROOT}/#", qos=1)
    delivered = {}
    for message in customer.receive_rest():
        # The broker counts down: it forwards the *remaining* lifetime.
        remaining = getattr(message.properties, "MessageExpiryInterval", None)
        delivered[message.topic] = remaining
        left = f"{remaining} s left" if remaining is not None else "no expiry"
        say(f"got {message.topic}: {text(message)!r} ({left})")
    customer.disconnect()

    clear_retained(shop, OFFERS)
    shop.disconnect()
    check(f"{ROOT}/flash-sale" not in delivered, "the flash sale expired and the broker dropped it")
    return Result(delivered)
