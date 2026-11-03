"""Lesson 9: MQTT 5 shared subscriptions."""
from __future__ import annotations

from dataclasses import dataclass

from mqttUtils import BrokerSettings

from ._kit import Peer, check, say, step, text

TITLE = "MQTT 5: shared subscriptions"

TOPIC = "lesson09/jobs/resize-image"
GROUP = "resizers"
WORKERS = 3
JOBS = 9


@dataclass
class Result:
    per_worker: dict[str, list[str]]  # worker -> jobs it got
    auditor: list[str]  # jobs the normal (non-shared) subscriber got
    jobs: list[str]  # jobs that were published


def run(settings: BrokerSettings) -> Result:
    shared_filter = f"$share/{GROUP}/{TOPIC}"
    step(1, f"{WORKERS} workers join the group {GROUP!r}; an auditor subscribes normally")
    workers = {}
    for number in range(1, WORKERS + 1):
        worker = Peer(f"lesson09-worker-{number}", settings)
        worker.connect()
        worker.subscribe(shared_filter, qos=1)
        workers[f"worker-{number}"] = worker
    say(f"workers subscribe to {shared_filter}")
    auditor = Peer("lesson09-auditor", settings)
    auditor.connect()
    auditor.subscribe(TOPIC, qos=1)
    say(f"auditor subscribes to {TOPIC}")

    step(2, f"The web app publishes {JOBS} jobs to {TOPIC}")
    jobs = [f"photo-{n}.jpg" for n in range(1, JOBS + 1)]
    app = Peer("lesson09-web-app", settings)
    app.connect()
    for job in jobs:
        app.publish(TOPIC, job, qos=1)
    app.disconnect()

    step(3, "Each job went to exactly one worker of the group")
    per_worker = {}
    for name, worker in workers.items():
        per_worker[name] = [text(m) for m in worker.receive_rest()]
        worker.disconnect()
        say(f"{name}: {', '.join(per_worker[name])}")
    audited = [text(m) for m in auditor.receive_rest()]
    auditor.disconnect()
    say(f"auditor: all {len(audited)} jobs")

    handled = sorted((job for got in per_worker.values() for job in got), key=jobs.index)
    check(handled == jobs, f"{len(handled)} jobs handled, none twice, none lost")
    return Result(per_worker, audited, jobs)
