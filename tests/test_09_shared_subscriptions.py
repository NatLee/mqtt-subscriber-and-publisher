"""Lesson 9: a shared subscription hands each message to one group member."""


def test_each_job_goes_to_exactly_one_worker(run_lesson):
    result = run_lesson(9)
    handled = [job for jobs in result.per_worker.values() for job in jobs]
    assert sorted(handled) == sorted(result.jobs)
    assert len(handled) == len(set(handled))
    # The broker spreads the load: every worker got some.
    assert all(result.per_worker.values())
    # A normal subscription still sees everything.
    assert result.auditor == result.jobs
