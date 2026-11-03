# Lessons

Ten short lessons, each one command against the course broker. Every lesson
prints what happens step by step, and its `.md` file explains the idea with a
sequence diagram and the output you should see.

```bash
docker compose run --rm course        # list the lessons
docker compose run --rm course 3      # run lesson 3
docker compose run --rm course all    # run them all
```

| # | Lesson | You'll see |
|---|---|---|
| 1 | [Connect and log in](01_connect.md) | Mosquitto 2 refusing anonymous clients, CONNACK reason codes, `$SYS` topics |
| 2 | [Topics and wildcards](02_topics.md) | which of five filters (`+`, `#`) catch which of six topics |
| 3 | [QoS 0, 1 and 2](03_qos.md) | the real packet exchange per QoS, QoS downgrade, a QoS 1 message delivered twice |
| 4 | [Retained messages](04_retained.md) | late subscribers getting the last known value, and deleting it |
| 5 | [Last will and testament](05_last_will.md) | the broker announcing a client that vanished, via keep-alive |
| 6 | [Clean and persistent sessions](06_sessions.md) | messages queued for an offline client, and what a clean start forgets |
| 7 | [MQTT 5: user properties](07_user_properties.md) | content type and header-like metadata riding along with a message |
| 8 | [MQTT 5: message expiry](08_message_expiry.md) | a stale offer disappearing from the broker |
| 9 | [MQTT 5: shared subscriptions](09_shared_subscriptions.md) | three workers splitting nine jobs |
| 10 | [MQTT 5: request / response](10_request_response.md) | response topic and correlation data pairing answers with questions |

The ideas in lessons 1 to 6 exist in MQTT 3.1.1 too (lesson 6 shows how its
session flag maps to MQTT 5). Lessons 7 to 10 are new in MQTT 5. All lessons
connect with MQTT 5, the current version of the standard, which both paho-mqtt
and Mosquitto 2 support.

## How a lesson is built

Each `NN_topic.py` has a `TITLE` and a `run(settings)` function. `run()` prints
the story and returns what it observed. The runner (`python -m lessons`) prints
the output; the matching test in [`tests/`](../tests) runs the same function
against the broker and asserts on the result. That's how CI knows every
explanation here is still true.

[`_kit.py`](_kit.py) keeps the plumbing out of the lessons. A `Peer` is a paho
`Client` that waits for the broker's answers (CONNACK, SUBACK, the end of the
QoS handshake), so a lesson reads top to bottom. Everything MQTT still goes
through the normal paho API, and `peer.client` is the paho client itself.

Each lesson uses its own topic prefix (`lesson04/...`) and client IDs
(`lesson04-display`). Lessons never see each other's messages, and a lesson
cleans up its retained messages when it starts, in case an earlier run stopped
halfway.
