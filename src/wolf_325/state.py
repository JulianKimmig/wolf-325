"""Runtime cache records and update callback types for the controller."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeAlias

from .types import JSONValue


@dataclass(slots=True)
class ValueState:
    """Hold the latest decoded and raw state for one logical register."""

    key: str
    value: JSONValue | None = None
    raw: JSONValue | None = None
    unit: str | None = None
    available: bool = False
    updated_at: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the stable public JSON representation of this cached value."""
        return {
            "value": self.value,
            "raw": self.raw,
            "unit": self.unit,
            "available": self.available,
            "updated_at": self.updated_at,
            "error": self.error,
        }


UpdateCallback: TypeAlias = Callable[[dict[str, Any]], Awaitable[None] | None]
