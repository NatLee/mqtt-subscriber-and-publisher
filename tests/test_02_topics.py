"""Lesson 2: the broker routes by topic filter exactly as the spec says."""
import pytest

from lessons import load


@pytest.fixture(scope="module")
def result(settings):
    return load(2).run(settings)


def test_broker_agrees_with_paho_matcher(result):
    assert result.received == result.expected


def test_wildcard_rules(result):
    received = result.received
    # Exact filter: one topic only.
    assert received["home/kitchen/temperature"] == ["home/kitchen/temperature"]
    # "+" is exactly one level: the 4-level door/state topic does not match.
    assert received["home/+/temperature"] == ["home/kitchen/temperature", "home/garage/temperature"]
    # "#" also matches the parent level itself ("home").
    assert received["home/#"][0] == "home"
    assert len(received["home/#"]) == 5
    # Wildcards can start a filter and be combined.
    assert received["+/kitchen/#"] == [
        "home/kitchen/temperature",
        "home/kitchen/humidity",
        "office/kitchen/temperature",
    ]
