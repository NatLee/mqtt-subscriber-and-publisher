"""mqttUtils.serialization: any plain data round-trips, code never runs."""
import datetime
import pickle

import numpy as np
import pytest

from mqttUtils import SAFE_GLOBALS, UnsafePayloadError, dumps, loads

# The payloads from example_send.py, plus the other built-in types.
PLAIN_DATA = [
    {"test1": 1234, "test2": "yee"},
    1234,
    b"ABCDEFG",
    ["1", "a", "b"],
    None,
    3.5,
    True,
    (1, "two"),
    {1, 2},
    frozenset({"x"}),
    complex(1, 2),
    bytearray(b"raw"),
    {"nested": [{"deep": (1, 2.0, None)}]},
]


@pytest.mark.parametrize("data", PLAIN_DATA, ids=lambda d: type(d).__name__)
def test_plain_data_round_trips(data):
    assert loads(dumps(data)) == data


# Senders on different Python versions pickle with protocol 4 or 5 by default.
@pytest.mark.parametrize("protocol", [4, 5])
@pytest.mark.parametrize(
    "array",
    [np.arange(6), np.arange(6.0).reshape(2, 3).T, np.array(["a", "bc"])],
    ids=["int", "non-contiguous-float", "str"],
)
def test_numpy_arrays_round_trip(array, protocol):
    restored = loads(pickle.dumps(array, protocol=protocol))
    assert restored.dtype == array.dtype
    np.testing.assert_array_equal(restored, array)


def test_numpy_scalars_round_trip():
    assert loads(dumps(np.float64(1.5))) == np.float64(1.5)


class RunsCode:
    """A payload that would call print() when unpickled with plain pickle."""

    def __reduce__(self):
        return (print, ("this must never run",))


def test_payload_that_calls_a_function_is_refused(capsys):
    payload = pickle.dumps(RunsCode())
    with pytest.raises(UnsafePayloadError, match="builtins.print"):
        loads(payload)
    assert "never run" not in capsys.readouterr().out


def test_other_classes_need_an_explicit_allow_list():
    payload = dumps(datetime.date(2026, 11, 4))
    with pytest.raises(UnsafePayloadError):
        loads(payload)
    allowed = SAFE_GLOBALS | {("datetime", "date")}
    assert loads(payload, allowed=allowed) == datetime.date(2026, 11, 4)


@pytest.mark.parametrize("payload", [b"not a pickle", b"", b"\x80\x05"])
def test_garbage_raises_instead_of_returning_something(payload):
    # MqttSubscriber.on_message catches these and skips the message.
    with pytest.raises((pickle.UnpicklingError, EOFError)):
        loads(payload)
