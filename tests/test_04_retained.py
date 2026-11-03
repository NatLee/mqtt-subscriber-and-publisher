"""Lesson 4: retained messages."""


def test_retained_messages(run_lesson):
    result = run_lesson(4)
    # A new subscriber gets the stored value at once, flagged as retained.
    assert result.first_join == ("21.5 C", True)
    # Current subscribers get updates live, not flagged.
    assert result.live == ("21.7 C", False)
    # Only the newest retained value is kept.
    assert result.second_join == ("21.7 C", True)
    # An empty retained payload deletes it.
    assert result.after_clear == []
