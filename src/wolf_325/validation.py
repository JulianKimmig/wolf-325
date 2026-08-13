"""Cross-register validation and named setting normalization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .catalogue import REGISTERS, resolve_register_name
from .errors import RegisterError, ValidationError
from .types import JSONScalar

RELATIONAL_SETTING_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "flow_preset_holiday_m3h",
        "flow_preset_low_m3h",
        "flow_preset_normal_m3h",
        "flow_preset_high_m3h",
    ),
    tuple(f"pwm_supply_{level}_pct" for level in ("holiday", "low", "normal", "high")),
    tuple(f"pwm_exhaust_{level}_pct" for level in ("holiday", "low", "normal", "high")),
    *((f"co2_sensor_{sensor}_low_ppm", f"co2_sensor_{sensor}_high_ppm") for sensor in range(1, 5)),
    *((f"analog_input_{channel}_min_v", f"analog_input_{channel}_max_v") for channel in range(1, 3)),
    (
        "geo_heat_exchanger_min_temperature_c",
        "geo_heat_exchanger_max_temperature_c",
    ),
)


def affected_relation_groups(settings: Mapping[str, object]) -> tuple[tuple[str, ...], ...]:
    """Return relational groups touched by submitted canonical setting keys.

    Args:
        settings: Canonical submitted setting values.

    Returns:
        Ordered groups containing at least one submitted key.
    """
    keys = set(settings)
    return tuple(group for group in RELATIONAL_SETTING_GROUPS if keys.intersection(group))


def validate_cross_settings(settings: Mapping[str, JSONScalar]) -> None:
    """Validate relationships that cannot be expressed by one register alone."""

    def numeric(key: str) -> float:
        """Return a previously normalized numeric setting."""
        value = settings[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(f"{key}: expected a normalized numeric value")
        return float(value)

    def ordered(keys: Sequence[str], label: str) -> None:
        """Ensure supplied members of an ordered preset sequence are nondecreasing."""
        available = [(key, settings[key]) for key in keys if key in settings]
        for (left_key, left), (right_key, right) in zip(
            available, available[1:], strict=False
        ):
            if (
                isinstance(left, (int, float))
                and isinstance(right, (int, float))
                and left > right
            ):
                raise ValidationError(
                    f"{label}: {left_key} ({left}) must not exceed "
                    f"{right_key} ({right})"
                )

    ordered(
        [
            "flow_preset_holiday_m3h",
            "flow_preset_low_m3h",
            "flow_preset_normal_m3h",
            "flow_preset_high_m3h",
        ],
        "airflow presets",
    )
    for prefix, label in (
        ("pwm_supply", "supply PWM presets"),
        ("pwm_exhaust", "exhaust PWM presets"),
    ):
        ordered(
            [f"{prefix}_{level}_pct" for level in ("holiday", "low", "normal", "high")],
            label,
        )
    for sensor in range(1, 5):
        low_key = f"co2_sensor_{sensor}_low_ppm"
        high_key = f"co2_sensor_{sensor}_high_ppm"
        if low_key in settings and high_key in settings:
            if numeric(low_key) > numeric(high_key):
                raise ValidationError(f"{low_key} must not exceed {high_key}")
    for channel in (1, 2):
        low_key = f"analog_input_{channel}_min_v"
        high_key = f"analog_input_{channel}_max_v"
        if low_key in settings and high_key in settings:
            if numeric(low_key) > numeric(high_key):
                raise ValidationError(f"{low_key} must not exceed {high_key}")
    low_key = "geo_heat_exchanger_min_temperature_c"
    high_key = "geo_heat_exchanger_max_temperature_c"
    if low_key in settings and high_key in settings:
        if numeric(low_key) >= numeric(high_key):
            raise ValidationError(f"{low_key} must be lower than {high_key}")


def normalize_settings(
    supplied: Mapping[str, Any],
    *,
    require_restorable: bool = False,
    allow_dangerous: bool = False,
) -> dict[str, JSONScalar]:
    """Resolve, authorize, normalize, and cross-validate named setting values."""
    normalized: dict[str, JSONScalar] = {}
    for supplied_key, value in supplied.items():
        key = resolve_register_name(supplied_key)
        register = REGISTERS[key]
        if not register.writable:
            raise RegisterError(f"{key} is read-only")
        if register.one_shot:
            raise RegisterError(
                f"{key} is a one-shot command and cannot be stored as desired state"
            )
        if register.dangerous and not allow_dangerous:
            raise RegisterError(
                f"{key} is a dangerous communication/reset setting; "
                "explicit opt-in is required"
            )
        if require_restorable and not register.restorable:
            raise RegisterError(f"{key} must not be restored automatically")
        normalized[key] = register.normalize(value)
    validate_cross_settings(normalized)
    return normalized
