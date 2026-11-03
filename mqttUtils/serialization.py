"""
Turn Python objects into MQTT payloads and back.

MQTT does not care what a payload is: the broker forwards bytes. This example
uses pickle so you can send a dict, a list, bytes or a NumPy array and get the
same object back on the other side.

Pickle has a sharp edge, though. Unpickling can call any function the data
names, and *anyone who may publish to your topic* chooses that data. On a public
broker that is the whole internet. So ``loads`` only rebuilds plain data: the
built-in types and NumPy arrays. Anything else raises ``UnsafePayloadError``.

If you control every publisher and need more types, pass a bigger ``allowed``
set, e.g. ``loads(payload, allowed=SAFE_GLOBALS | {("datetime", "datetime")})``.
For data shared with other languages, prefer JSON.
"""
from __future__ import annotations

import io
import pickle
from collections.abc import Set as AbstractSet
from typing import Any

Global = tuple[str, str]

# Everything a payload may ask the unpickler to import, as (module, name).
# dict, list, tuple, str, bytes, int, float, bool and None need no import.
SAFE_GLOBALS: AbstractSet[Global] = frozenset(
    {
        ("builtins", "bytearray"),
        ("builtins", "complex"),
        ("builtins", "frozenset"),
        ("builtins", "set"),
        # NumPy arrays and scalars. NumPy 2 renamed numpy.core to numpy._core,
        # so both spellings appear in payloads made by different senders.
        ("numpy", "dtype"),
        ("numpy", "ndarray"),
        *(
            (f"{core}.{module}", name)
            for core in ("numpy.core", "numpy._core")
            for module, name in (
                ("multiarray", "_reconstruct"),
                ("multiarray", "scalar"),
                ("numeric", "_frombuffer"),
            )
        ),
    }
)


class UnsafePayloadError(pickle.UnpicklingError):
    """The payload wants to import something outside the allowed set."""


class _RestrictedUnpickler(pickle.Unpickler):
    # This is the approach the Python docs describe under "Restricting Globals".
    def __init__(self, file: io.BytesIO, allowed: AbstractSet[Global]):
        super().__init__(file)
        self._allowed = allowed

    def find_class(self, module: str, name: str) -> Any:
        if (module, name) not in self._allowed:
            raise UnsafePayloadError(f"refusing to load {module}.{name} from a message")
        return super().find_class(module, name)


def dumps(data: Any) -> bytes:
    """Encode any picklable object as an MQTT payload."""
    return pickle.dumps(data)


def loads(payload: bytes, allowed: AbstractSet[Global] = SAFE_GLOBALS) -> Any:
    """Decode a payload made by ``dumps``, rebuilding only allowed types."""
    return _RestrictedUnpickler(io.BytesIO(payload), allowed).load()
