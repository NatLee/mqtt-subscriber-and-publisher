"""Lesson 1: the broker refuses strangers and lets the demo account in."""
import pytest

from lessons import load

# MQTT 5 has two reason codes a broker may use to turn a login down.
REFUSALS = {"Not authorized", "Bad user name or password"}


@pytest.fixture(scope="module")
def result(settings):
    return load(1).run(settings)


def test_anonymous_and_wrong_password_are_refused(result):
    assert result.anonymous in REFUSALS
    assert result.wrong_password in REFUSALS


def test_demo_account_gets_a_fresh_session_and_reads_sys(result):
    assert result.accepted == "Success"
    assert result.session_present is False
    # compose.yaml runs Mosquitto 2.x
    assert result.broker_version.startswith("mosquitto version 2.")
