"""Lesson 6: persistent sessions queue QoS 1 messages; clean starts forget."""


def test_sessions(run_lesson):
    result = run_lesson(6)
    assert result.first_session_present is False
    assert result.resumed_session_present is True
    # Mosquitto does not queue QoS 0 messages for offline clients (queue_qos0_messages false).
    assert result.resumed_messages == ["alert 2 (QoS 1)"]
    assert result.clean_session_present is False
    assert result.clean_messages == []
