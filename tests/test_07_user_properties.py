"""Lesson 7: MQTT 5 properties travel with the message, unchanged."""
from lessons import load

LESSON = load(7).module


def test_properties_arrive_intact(run_lesson):
    result = run_lesson(7)
    assert result.reading == LESSON.READING
    assert result.content_type == "application/json"
    assert result.payload_is_utf8 is True
    # Order kept, repeated names kept.
    assert result.user_properties == LESSON.USER_PROPERTIES
