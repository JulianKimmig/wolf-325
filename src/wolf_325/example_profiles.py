"""Canonical portable example profiles shared by all controller hosts."""

from __future__ import annotations

import copy
from typing import Any, Final

_EXAMPLE_PROFILES: Final[dict[str, dict[str, Any]]] = {
    "normal": {
        "description": "Normal continuous ventilation",
        "settings": {
            "remote_ventilation_level": "normal",
            "remote_control_mode": "level",
            "remote_standby": False,
        },
    },
    "night": {
        "description": "Quiet night ventilation",
        "settings": {
            "remote_ventilation_level": "low",
            "remote_control_mode": "level",
            "remote_standby": False,
        },
    },
    "boost": {
        "description": "Maximum preset ventilation",
        "settings": {
            "remote_ventilation_level": "high",
            "remote_control_mode": "level",
            "remote_standby": False,
        },
    },
    "away": {
        "description": "Holiday ventilation at the lowest preset",
        "settings": {
            "remote_ventilation_level": "holiday",
            "remote_control_mode": "level",
            "remote_standby": False,
        },
    },
    "summer-night": {
        "description": "Night flow with bypass forced open",
        "extends": ["night"],
        "settings": {"bypass_mode": "open"},
    },
}


def example_profile_documents() -> dict[str, dict[str, Any]]:
    """Return an isolated canonical profile catalogue keyed without suffixes."""
    return copy.deepcopy(_EXAMPLE_PROFILES)
