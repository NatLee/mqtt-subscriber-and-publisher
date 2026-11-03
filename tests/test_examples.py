"""The original example: example_send.py -> broker -> example_subscriber.py."""
from __future__ import annotations

import os
import pickle
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from lessons._kit import COURSE_ENV, Peer
from mqttUtils import DEFAULT_PORT, MqttSender, MqttSubscriber
from mqttUtils.settings import read_env_file

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


def env_without_mqtt(**extra: str) -> dict:
    """The environment of someone who never set any MQTT_* variable."""
    clean = {key: value for key, value in os.environ.items() if not key.startswith("MQTT_")}
    return {**clean, **extra}


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("localhost", 0))
        return probe.getsockname()[1]


@pytest.mark.parametrize("script", ["example_send.py", "example_subscriber.py"])
def test_examples_default_to_localhost_and_explain_a_missing_broker(script):
    # Only the port is changed (to one nobody listens on); the host is the default.
    port = free_port()
    result = subprocess.run(
        [sys.executable, script],
        cwd=REPO,
        env=env_without_mqtt(MQTT_PORT=str(port)),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    assert result.returncode == 1
    assert f"Can't reach an MQTT broker at localhost:{port}" in result.stderr
    assert "docker compose up -d --wait broker" in result.stderr
    assert "Traceback" not in result.stderr


def broker_on_localhost() -> bool:
    try:
        socket.create_connection(("localhost", DEFAULT_PORT), timeout=1).close()
    except OSError:
        return False
    return True


# The default broker is the one compose publishes on localhost, which is only
# "localhost" when Python runs on the host (CI's host-python jobs), not inside
# the course containers.
@pytest.mark.skipif(not broker_on_localhost(), reason=f"no broker on localhost:{DEFAULT_PORT}")
def test_examples_reach_the_course_broker_with_no_settings_at_all():
    sender = subprocess.run(
        [sys.executable, "example_send.py"],
        cwd=REPO,
        env=env_without_mqtt(),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    assert sender.returncode == 0, sender.stderr
    demo_user = read_env_file(COURSE_ENV)["MQTT_USERNAME"]
    assert sender.stdout.strip() == f"Sent 4 messages to localhost:{DEFAULT_PORT} as {demo_user!r}"


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
