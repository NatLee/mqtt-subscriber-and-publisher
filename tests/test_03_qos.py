"""Lesson 3: packet exchanges per QoS, QoS downgrade, and QoS 1 redelivery."""
import pytest

from lessons import load

QOS = load(3).module.LEVELS


@pytest.fixture(scope="module")
def result(settings):
    return load(3).run(settings)


@pytest.mark.parametrize("qos", [0, 1, 2])
def test_each_hop_runs_the_handshake_of_its_qos(result, qos):
    publisher, subscriber = result.handshakes[qos]
    expected = QOS[qos][1]  # e.g. PUBLISH, PUBREC, PUBREL, PUBCOMP
    assert [p.kind for p in publisher] == expected
    assert [p.kind for p in subscriber] == expected
    # Packets alternate direction; the publisher speaks first, the subscriber listens first.
    assert [p.sent for p in publisher] == [i % 2 == 0 for i in range(len(expected))]
    assert [p.sent for p in subscriber] == [i % 2 == 1 for i in range(len(expected))]
    assert publisher[0].qos == subscriber[0].qos == qos


@pytest.mark.parametrize("qos", [1, 2])
def test_acknowledgements_quote_the_packet_id(result, qos):
    for leg in result.handshakes[qos]:
        assert len({p.mid for p in leg}) == 1
        assert leg[0].mid


def test_qos0_publish_has_no_packet_id(result):
    for leg in result.handshakes[0]:
        assert leg[0].mid is None


def test_subscription_qos_caps_delivery(result):
    assert result.granted_qos == 0
    assert result.delivered_qos == 0


def test_unacknowledged_qos1_message_is_redelivered_with_dup(result):
    assert result.dup_flags == [False, True]
