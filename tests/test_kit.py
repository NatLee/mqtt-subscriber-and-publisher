"""Course plumbing that needs no broker: settings, packet-log parsing, the runner."""
import pytest

from lessons import __main__ as runner
from lessons import discover
from lessons._kit import COURSE_ENV, Packet, course_settings, parse_packet_log, read_env_file
from mqttUtils import BrokerSettings


def test_settings_from_env_and_defaults():
    assert BrokerSettings.from_env({}, default_host="example.org") == BrokerSettings("example.org", 1883)
    env = {"MQTT_HOST": "broker", "MQTT_PORT": "1884", "MQTT_USERNAME": "u", "MQTT_PASSWORD": "p"}
    assert BrokerSettings.from_env(env) == BrokerSettings("broker", 1884, "u", "p")
    # Empty values count as unset (compose passes empty strings through).
    assert BrokerSettings.from_env({"MQTT_USERNAME": ""}).username is None


def test_describe_never_shows_the_password():
    assert "secret" not in BrokerSettings("h", 1, "u", "secret").describe()


def test_course_settings_use_course_env_unless_overridden():
    demo = read_env_file(COURSE_ENV)
    assert demo["MQTT_USERNAME"] and demo["MQTT_PASSWORD"]
    assert course_settings({}).username == demo["MQTT_USERNAME"]
    assert course_settings({}).host == "localhost"
    assert course_settings({"MQTT_USERNAME": "me"}).username == "me"


# Real lines from paho-mqtt's on_log callback (MQTT 5 client).
@pytest.mark.parametrize(
    "line, packet",
    [
        ("Sending PUBLISH (d0, q2, r0, m3), 'b'lesson03/handshake'', properties=[], ... (10 bytes)",
         Packet(True, "PUBLISH", qos=2, dup=False, mid=3)),
        ("Received PUBLISH (d1, q1, r0, m1), 'lesson03/orders', properties={}, ...  (8 bytes)",
         Packet(False, "PUBLISH", qos=1, dup=True, mid=1)),
        ("Sending PUBLISH (d0, q0, r0, m1), 'b'x'', properties=[], ... (1 bytes)",
         Packet(True, "PUBLISH", qos=0, dup=False, mid=None)),
        ("Received PUBREC (Mid: 3)", Packet(False, "PUBREC", mid=3)),
        ("Sending PUBCOMP (Mid: 2)", Packet(True, "PUBCOMP", mid=2)),
        ("Received SUBACK", Packet(False, "SUBACK")),
        ("Caught exception in on_message: boom", None),
    ],
)
def test_parse_packet_log(line, packet):
    assert parse_packet_log(line) == packet


def test_lessons_are_numbered_without_gaps():
    numbers = [lesson.number for lesson in discover()]
    assert numbers == list(range(1, len(numbers) + 1))


def test_every_lesson_has_its_explanation_with_a_diagram():
    for lesson in discover():
        doc = COURSE_ENV.parent / "lessons" / f"{lesson.module_name}.md"
        assert doc.is_file(), f"missing {doc.name}"
        assert "```mermaid" in doc.read_text(encoding="utf-8"), f"{doc.name} has no diagram"


def test_runner_lists_lessons_and_rejects_unknown_ones(capsys):
    assert runner.main([]) == 0
    listing = capsys.readouterr().out
    assert all(lesson.title in listing for lesson in discover())
    assert runner.main(["99"]) == 2
    assert runner.main(["three"]) == 2
