"""Virtual value definitions and recalculation for measured air streams."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from .codecs import slug
from .errors import RegisterError
from .types import JSONValue, PollTier


def calculate_dew_point_c(
    temperature_c: float, relative_humidity_pct: float
) -> float:
    """Calculate dew point with the Magnus formula.

    Args:
        temperature_c: Air temperature in degrees Celsius.
        relative_humidity_pct: Relative humidity in whole percent.

    Returns:
        Dew-point temperature rounded to one decimal degree Celsius.

    Raises:
        ValueError: If either measurement is non-finite or humidity is outside
            the physically meaningful interval ``(0, 100]``.
    """
    temperature = float(temperature_c)
    humidity = float(relative_humidity_pct)
    if not math.isfinite(temperature) or not math.isfinite(humidity):
        raise ValueError("dew-point measurements must be finite")
    if temperature <= -243.12:
        raise ValueError("temperature is outside the Magnus formula domain")
    if not 0.0 < humidity <= 100.0:
        raise ValueError("relative humidity must be greater than 0 and at most 100")
    coefficient_a = 17.62
    coefficient_b = 243.12
    gamma = math.log(humidity / 100.0) + (
        coefficient_a * temperature / (coefficient_b + temperature)
    )
    return round(coefficient_b * gamma / (coefficient_a - gamma), 1)


@dataclass(frozen=True, slots=True)
class VirtualValueDef:
    """Describe one read-only value calculated from cached dependencies.

    Attributes:
        key: Stable canonical state key.
        description: Human-readable value name.
        unit: Engineering unit of the calculated result.
        dependencies: Ordered canonical physical value keys.
        calculate: Pure calculation receiving dependency values in order.
        poll: Tier whose freshness governs consumers of this value.
    """

    key: str
    description: str
    unit: str
    dependencies: tuple[str, ...]
    calculate: Callable[..., JSONValue]
    poll: PollTier = "fast"


VIRTUAL_VALUES: Final[dict[str, VirtualValueDef]] = {
    definition.key: definition
    for definition in (
        VirtualValueDef(
            key="supply_dew_point_c",
            description="Supply air dew point",
            unit="°C",
            dependencies=(
                "supply_temperature_c",
                "supply_relative_humidity_pct",
            ),
            calculate=calculate_dew_point_c,
        ),
        VirtualValueDef(
            key="exhaust_dew_point_c",
            description="Exhaust air dew point",
            unit="°C",
            dependencies=(
                "exhaust_temperature_c",
                "exhaust_relative_humidity_pct",
            ),
            calculate=calculate_dew_point_c,
        ),
    )
}

_DEPENDENTS: Final[dict[str, tuple[VirtualValueDef, ...]]] = {
    dependency: tuple(
        definition
        for definition in VIRTUAL_VALUES.values()
        if dependency in definition.dependencies
    )
    for dependency in {
        key for definition in VIRTUAL_VALUES.values() for key in definition.dependencies
    }
}


def resolve_value_name(name: str) -> str:
    """Resolve a physical or virtual canonical value name.

    Args:
        name: User-facing canonical or normalized value name.

    Returns:
        Canonical physical register or virtual value key.

    Raises:
        RegisterError: If no physical or virtual value matches.
    """
    from .catalogue import resolve_register_name

    key = slug(name)
    if key in VIRTUAL_VALUES:
        return key
    return resolve_register_name(name)


class DerivedValueMixin:
    """Maintain virtual cached values after physical dependency updates."""

    async def _update_dependent_values(self, source_key: str, now: str) -> bool:
        """Recalculate virtual values affected by one physical state change.

        Args:
            source_key: Canonical physical value key that changed or refreshed.
            now: UTC ISO timestamp shared with the source state update.

        Returns:
            Whether any dependent virtual state observably changed.
        """
        changed_any = False
        for definition in _DEPENDENTS.get(source_key, ()):
            states = [self._values[key] for key in definition.dependencies]
            if any(state.updated_at is None for state in states):
                continue
            unavailable = [state.key for state in states if not state.available]
            if unavailable:
                value: JSONValue | None = None
                error = "dependency unavailable: " + ", ".join(unavailable)
                available = False
            else:
                try:
                    value = definition.calculate(*(state.value for state in states))
                    error = None
                    available = True
                except (TypeError, ValueError) as exc:
                    value = None
                    error = f"calculation error: {exc}"
                    available = False
            state = self._values[definition.key]
            changed = (
                state.value != value
                or state.available != available
                or state.error != error
            )
            state.value = value
            state.raw = None
            state.available = available
            state.error = error
            state.updated_at = now
            if changed:
                await self._emit_update(state)
                changed_any = True
        return changed_any


__all__ = [
    "DerivedValueMixin",
    "VIRTUAL_VALUES",
    "VirtualValueDef",
    "calculate_dew_point_c",
    "resolve_value_name",
]
