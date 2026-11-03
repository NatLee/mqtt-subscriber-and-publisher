"""
Where the broker is and how to log in, read from environment variables.

    MQTT_HOST      broker host name          (default: the caller's choice)
    MQTT_PORT      broker port               (default: 1883)
    MQTT_USERNAME  user name, empty = none   (default: none)
    MQTT_PASSWORD  password                  (default: none)
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

# The port IANA assigned to MQTT over plain TCP.
DEFAULT_PORT = 1883


@dataclass(frozen=True)
class BrokerSettings:
    """Connection details for one MQTT broker."""

    host: str
    port: int = DEFAULT_PORT
    username: str | None = None
    password: str | None = None

    @classmethod
    def from_env(
        cls, environ: Mapping[str, str] = os.environ, *, default_host: str = "localhost"
    ) -> BrokerSettings:
        """Build settings from MQTT_* variables, falling back to ``default_host``."""
        return cls(
            host=environ.get("MQTT_HOST") or default_host,
            port=int(environ.get("MQTT_PORT") or DEFAULT_PORT),
            username=environ.get("MQTT_USERNAME") or None,
            password=environ.get("MQTT_PASSWORD") or None,
        )

    def describe(self) -> str:
        """``host:port`` plus the user name, for log lines (never the password)."""
        who = f" as {self.username!r}" if self.username else " without a user name"
        return f"{self.host}:{self.port}{who}"
