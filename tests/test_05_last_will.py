"""Lesson 5: the broker publishes a will only for clients that vanish."""
from lessons import load

LESSON = load(5).module


def test_will_only_for_the_vanished_client(run_lesson):
    result = run_lesson(5)
    assert result.timeline == {
        "sensor-a": ["online", LESSON.GOODBYE],
        "sensor-b": ["online", LESSON.WILL],
    }
    # The broker waits 1.5 x KEEPALIVE (3 s) of silence. Mosquitto keeps that
    # time in whole seconds, so it may fire up to a second early (seen: 2.1 s),
    # and a little late. Either way, not at once and not much later.
    nominal = LESSON.KEEPALIVE * 1.5
    assert nominal - 1.5 < result.will_after < nominal + 3
    assert result.retained == {"sensor-a": LESSON.GOODBYE, "sensor-b": LESSON.WILL}
