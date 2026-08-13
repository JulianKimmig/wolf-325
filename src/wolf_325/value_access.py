"""Public accessors for physical and virtual cached controller values."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from .catalogue import REGISTERS
from .derived_values import VIRTUAL_VALUES, resolve_value_name
from .types import JSONValue


class ValueAccessMixin:
    """Expose cache reads, snapshots, and physical or virtual refreshes."""

    def get_value(self, name: str, default: Any = None) -> Any:
        """Return a cached value or the supplied default when unavailable.

        Args:
            name: Physical register or virtual value name.
            default: Value returned when the cached state is unavailable.

        Returns:
            Decoded/calculated cached value or ``default``.
        """
        state = self._values[resolve_value_name(name)]
        return state.value if state.available else default

    def get_state(self, name: str) -> dict[str, Any]:
        """Return an isolated public state record for one named value.

        Args:
            name: Physical register or virtual value name.

        Returns:
            JSON-compatible copy of the cached state.
        """
        return copy.deepcopy(self._values[resolve_value_name(name)].as_dict())

    def snapshot(self, *, available_only: bool = False) -> dict[str, Any]:
        """Return a timestamped JSON-compatible snapshot of controller state.

        Args:
            available_only: Whether to omit unavailable physical and virtual values.

        Returns:
            Complete controller metadata and cached value mapping.
        """
        values = {
            key: state.as_dict()
            for key, state in sorted(self._values.items())
            if not available_only or state.available
        }
        return {
            "connected": self.connected,
            "connection_generation": self._connection_generation,
            "last_connection_error": self._last_connection_error,
            "last_poll_at": copy.deepcopy(self._last_poll_at),
            "last_profile": self.config.get("last_profile") if self.config else None,
            "desired": self.desired,
            "values": values,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    async def refresh(self, name: str) -> JSONValue | None:
        """Refresh one physical value or all dependencies of a virtual value.

        Args:
            name: Physical register or virtual value name.

        Returns:
            Latest decoded or calculated value, or ``None`` when unavailable.
        """
        key = resolve_value_name(name)
        virtual = VIRTUAL_VALUES.get(key)
        if virtual is None:
            await self._read_definition(REGISTERS[key])
        else:
            for dependency in virtual.dependencies:
                await self._read_definition(REGISTERS[dependency])
        return self._values[key].value


__all__ = ["ValueAccessMixin"]
