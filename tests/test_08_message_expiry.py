"""Lesson 8: the broker drops expired messages and counts down the rest."""
from lessons import load

LESSON = load(8).module
ROOT = LESSON.ROOT


def test_expired_message_is_dropped(run_lesson):
    delivered = run_lesson(8).delivered
    assert set(delivered) == {f"{ROOT}/weekly-menu", f"{ROOT}/opening-hours"}
    # Published with 3600 s to live, read LESSON.WAIT (3) s later.
    assert 3600 - 60 < delivered[f"{ROOT}/weekly-menu"] <= 3600 - LESSON.WAIT + 1
    # No expiry interval: the message never expires.
    assert delivered[f"{ROOT}/opening-hours"] is None
