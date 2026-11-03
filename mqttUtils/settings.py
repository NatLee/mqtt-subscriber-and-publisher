"""
Where the broker is and how to log in, read from environment variables.

    MQTT_HOST      broker host name          (default: localhost)
    MQTT_PORT      broker port               (default: 1883)
    MQTT_USERNAME  user name, empty = none   (default: none)
    MQTT_PASSWORD  password                  (default: none)

A defaults file (KEY=VALUE lines, like course.env) can describe the default
broker's login. It only applies while MQTT_HOST is unset: point MQTT_HOST at
another broker and you bring your own login, so the demo account is never sent
to a broker it doesn't belong to.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# The course broker publishes its port on this machine.
DEFAULT_HOST = "localhost"
# The port IANA assigned to MQTT over plain TCP.
DEFAULT_PORT = 1883

# What to do when the default broker isn't running.
START_BROKER_HINT = (
    "Is the broker running? The course broker starts with:  docker compose up -d --wait broker"
)


def read_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines (the format docker compose uses for env files)."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


@dataclass(frozen=True)
class BrokerSettings:
    """Connection details for one MQTT broker."""

    host: str
    port: int = DEFAULT_PORT
    username: str | None = None
    password: str | None = None

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] = os.environ,
        *,
        defaults_file: Path | None = None,
    ) -> BrokerSettings:
        """Build settings from MQTT_* variables.

        Missing values come from ``defaults_file`` (only while MQTT_HOST is
        unset, see the module docstring), then from DEFAULT_HOST and
        DEFAULT_PORT.
        """
        values = dict(environ)
        if defaults_file is not None and not values.get("MQTT_HOST"):
            values = {**read_env_file(defaults_file), **values}
        return cls(
            host=values.get("MQTT_HOST") or DEFAULT_HOST,
            port=int(values.get("MQTT_PORT") or DEFAULT_PORT),
            username=values.get("MQTT_USERNAME") or None,
            password=values.get("MQTT_PASSWORD") or None,
        )

    def describe(self) -> str:
        """``host:port`` plus the user name, for log lines (never the password)."""
        who = f" as {self.username!r}" if self.username else " without a user name"
        return f"{self.host}:{self.port}{who}"

    def unreachable(self, error: OSError) -> str:
        """A readable message for a failed TCP connection, with what to do next."""
        return f"Can't reach an MQTT broker at {self.host}:{self.port} ({error}).\n{START_BROKER_HINT}"
