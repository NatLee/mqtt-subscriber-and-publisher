"""
Fixtures shared by the tests. Most tests talk to a real broker:

    docker compose run --rm python -m pytest      (broker started for you)
    docker compose up -d --wait broker && pytest   (Python on your machine)
"""
from __future__ import annotations

import socket

import pytest

from lessons import load
from lessons._kit import course_settings
from mqttUtils import BrokerSettings


@pytest.fixture(scope="session")
def settings() -> BrokerSettings:
    """The course broker; fails (not skips) when it is not running."""
    broker = course_settings()
    try:
        socket.create_connection((broker.host, broker.port), timeout=3).close()
    except OSError as error:
        pytest.fail(
            f"No MQTT broker at {broker.host}:{broker.port} ({error}). "
            "Start it with: docker compose up -d --wait broker",
            pytrace=False,
        )
    return broker


@pytest.fixture
def run_lesson(settings):
    """run_lesson(3) runs lesson 3 against the broker and returns its Result."""
    return lambda number: load(number).run(settings)
