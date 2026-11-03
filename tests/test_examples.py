"""The original example: example_send.py -> broker -> example_subscriber.py."""
from __future__ import annotations

import os
import pickle
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from lessons._kit import Peer
from mqttUtils import MqttSender, MqttSubscriber

REPO = Path(__file__).resolve().parent.parent
TIMEOUT = 10

# What the README has always shown for the subscriber.
EXPECTED = [
    "yee {'test1': 1234, 'test2': 'yee'}",
    "yoo 1234",
    "yoo b'ABCDEFG'",
    "yoo ['1', 'a', 'b']",
]


def env_for(settings) -> dict:
    return {
        **os.environ,
        "MQTT_HOST": settings.host,
        "MQTT_PORT": str(settings.port),
        "MQTT_USERNAME": settings.username or "",
        "MQTT_PASSWORD": settings.password or "",
    }


class Lines:
    """Read a process's stdout on a thread so waiting can time out."""

    def __init__(self, process: subprocess.Popen):
        self.queue: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._pump, args=(process.stdout,), daemon=True).start()

    def _pump(self, stream) -> None:
        for line in stream:
            self.queue.put(line.rstrip("\n"))

    def next(self) -> str:
        return self.queue.get(timeout=TIMEOUT)


@pytest.mark.skipif(os.name == "nt", reason="stops the subscriber with SIGINT (POSIX only)")
def test_send_and_background_subscriber_scripts(settings):
    subscriber = subprocess.Popen(
        [sys.executable, "-u", "example_subscriber.py"],
        cwd=REPO,
        env=env_for(settings),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        lines = Lines(subscriber)
        assert lines.next() == "Connected with result code 0"
        assert lines.next() == "Subscribed to yoo, yee"

        sender = subprocess.run(
            [sys.executable, "example_send.py"],
            cwd=REPO,
            env=env_for(settings),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        assert sender.returncode == 0, sender.stderr
        assert [lines.next() for _ in EXPECTED] == EXPECTED

        subscriber.send_signal(signal.SIGINT)  # what Ctrl+C does
        assert lines.next() == "Exit!"
        assert subscriber.wait(timeout=TIMEOUT) == 0
    finally:
        subscriber.kill()


class RunsCode:
    def __reduce__(self):
        return (print, ("PWNED",))


def test_subscriber_skips_bad_payloads_and_keeps_listening(settings, capsys):
    """Regression: unpickling ran attacker code, and one bad payload killed the thread."""
    topic = "tests/examples/hostile"
    subscriber = MqttSubscriber(
        settings.host, [topic], settings.port, username=settings.username, password=settings.password
    )
    subscriber.client.loop_start()
    try:
        deadline = time.monotonic() + TIMEOUT
        while "Subscribed" not in capsys.readouterr().out:
            assert time.monotonic() < deadline, "subscriber never subscribed"
            time.sleep(0.05)

        attacker = Peer("tests-attacker", settings)
        attacker.connect()
        attacker.publish(topic, pickle.dumps(RunsCode()), qos=1)
        attacker.publish(topic, b"plain text, not a pickle", qos=1)
        attacker.disconnect()
        MqttSender(
            topic, settings.host, settings.port, username=settings.username, password=settings.password
        ).send({"still": "alive"})

        output = ""
        while "{'still': 'alive'}" not in output:
            assert time.monotonic() < deadline + TIMEOUT, f"subscriber stopped; output: {output!r}"
            time.sleep(0.05)
            output += capsys.readouterr().out
    finally:
        subscriber.client.disconnect()
        subscriber.client.loop_stop()

    assert "PWNED" not in output
    skipped = [line for line in output.splitlines() if "<skipped" in line]
    assert len(skipped) == 2
    assert "refusing to load builtins.print" in skipped[0]
