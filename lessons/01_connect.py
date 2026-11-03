"""Lesson 1: connect and log in."""
from __future__ import annotations

from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import ConnectionRefused, Peer, check, say, step, text

TITLE = "Connect and log in"


@dataclass
class Result:
    anonymous: str  # reason the broker gave a client without a user name
    wrong_password: str  # reason for a bad password
    accepted: str  # reason for the demo account
    session_present: bool
    broker_version: str


def try_connect(peer: Peer) -> str:
    """Connect, return the broker's reason code as text, and hang up again."""
    try:
        connack = peer.connect()
    except ConnectionRefused as refused:
        return str(refused.reason)
    peer.disconnect()
    return str(connack.reason)


def run(settings: BrokerSettings) -> Result:
    step(1, "Connect without a user name")
    anonymous = try_connect(Peer("lesson01-anonymous", settings, login=False))
    check(anonymous != "Success", f"CONNACK: {anonymous}  (Mosquitto 2 refuses anonymous clients)")

    step(2, "Connect with a wrong password")
    wrong = try_connect(Peer("lesson01-guesser", settings, password="not-the-password"))
    check(wrong != "Success", f"CONNACK: {wrong}")

    step(3, f"Connect as {settings.username!r} from course.env")
    student = Peer("lesson01-student", settings)
    connack = student.connect()
    check(not connack.reason.is_failure, f"CONNACK: {connack.reason}")
    say(f"session present: {connack.session_present}  (a brand-new session)")
    limits = connack.properties.json() if connack.properties else {}
    if limits:
        say("the broker also told us its limits: " + ", ".join(f"{k}={v}" for k, v in limits.items()))

    step(4, "Ask the broker who it is")
    # $SYS/... topics are written by the broker itself; the version is retained,
    # so it arrives as soon as we subscribe (more on retained messages in lesson 4).
    student.subscribe("$SYS/broker/version")
    version = text(student.receive())
    say(f"$SYS/broker/version = {version!r}")
    student.disconnect()

    return Result(anonymous, wrong, str(connack.reason), connack.session_present, version)
