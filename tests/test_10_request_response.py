"""Lesson 10: response topic + correlation data pair answers with requests."""


def test_answers_match_requests(run_lesson):
    result = run_lesson(10)
    # sum([1, 2, 3]), sum([10, 20]), sum([7])
    assert result.answers == result.expected == {"req-1": 6, "req-2": 30, "req-3": 7}
