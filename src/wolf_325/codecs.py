"""Pure validation and wire codecs for WOLF/Brink register definitions."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from .errors import RegisterError, ValidationError
from .register import RegisterDef
from .types import JSONScalar, JSONValue


def slug(value: str) -> str:
    """Normalize human-facing names to stable lowercase underscore tokens."""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _coerce_bool(value: Any, *, key: str) -> bool:
    """Coerce explicit conventional boolean forms or raise validation failure."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = slug(value)
        if text in {"1", "true", "yes", "on", "enabled", "enable"}:
            return True
        if text in {"0", "false", "no", "off", "disabled", "disable"}:
            return False
    raise ValidationError(f"{key}: expected a boolean, got {value!r}")


def _coerce_number(value: Any, *, key: str) -> float:
    """Coerce a finite real number while rejecting booleans and invalid text."""
    if isinstance(value, bool):
        raise ValidationError(f"{key}: boolean is not a number")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError as exc:
            raise ValidationError(f"{key}: expected a number, got {value!r}") from exc
        if math.isfinite(number):
            return number
    raise ValidationError(f"{key}: expected a finite number, got {value!r}")


def _format_scaled(value: float, scale: float) -> int | float:
    """Round a scaled value to the precision implied by its register scale."""
    if math.isclose(scale, 1.0):
        return int(round(value))
    decimals = max(0, int(round(-math.log10(scale)))) if scale < 1 else 6
    return round(value, decimals)


def enum_reverse(register: RegisterDef) -> dict[str, int]:
    """Build the canonical and aliased label-to-wire mapping for an enum."""
    reverse = {slug(label): raw for raw, label in (register.enum or {}).items()}
    for alias, canonical in register.enum_aliases.items():
        canonical_slug = slug(canonical)
        if canonical_slug not in reverse:
            raise RuntimeError(
                f"bad enum alias for {register.key}: {alias} -> {canonical}"
            )
        reverse[slug(alias)] = reverse[canonical_slug]
    return reverse


def _normalize_enum(register: RegisterDef, value: Any) -> str:
    """Normalize enum labels, aliases, and supported raw integer values."""
    assert register.enum is not None
    if isinstance(value, bool):
        raise ValidationError(f"{register.key}: boolean is not an enum value")
    if isinstance(value, int):
        if value not in register.enum:
            raise ValidationError(
                f"{register.key}: {value} is not valid; allowed raw values: "
                f"{sorted(register.enum)}"
            )
        return register.enum[value]
    if isinstance(value, str):
        reverse = enum_reverse(register)
        candidate = slug(value)
        if candidate in reverse:
            return register.enum[reverse[candidate]]
        if value.strip().lstrip("-").isdigit():
            return _normalize_enum(register, int(value))
        allowed = ", ".join(register.enum.values())
        raise ValidationError(
            f"{register.key}: expected one of [{allowed}], got {value!r}"
        )
    raise ValidationError(f"{register.key}: invalid enum value {value!r}")


def _normalize_pair(register: RegisterDef, value: Any) -> tuple[int, int]:
    """Normalize supported time/date pair inputs before codec-specific bounds."""
    separator = "-" if register.codec == "packed_month_day" else ":"
    pattern = r"\d{1,2}-\d{1,2}" if separator == "-" else r"\d{1,2}:\d{1,2}"
    if isinstance(value, str) and re.fullmatch(pattern, value.strip()):
        left_text, right_text = value.strip().split(separator, 1)
        return int(left_text), int(right_text)
    if isinstance(value, Mapping):
        names = {
            "packed_hm": ("hour", "minute"),
            "packed_month_day": ("month", "day"),
            "packed_weekday_second": ("weekday", "second"),
        }[register.codec]
        try:
            return int(value[names[0]]), int(value[names[1]])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"{register.key}: invalid pair mapping {value!r}") from exc
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == 2
    ):
        return int(value[0]), int(value[1])
    raise ValidationError(f"{register.key}: expected a two-part date/time value")


def _normalize_packed(register: RegisterDef, value: Any) -> str:
    """Normalize packed hour/date/weekday register values to stable strings."""
    left, right = _normalize_pair(register, value)
    if register.codec == "packed_hm":
        if not 0 <= left <= 23 or not 0 <= right <= 59:
            raise ValidationError(f"{register.key}: invalid time {left:02d}:{right:02d}")
        return f"{left:02d}:{right:02d}"
    if register.codec == "packed_month_day":
        try:
            datetime(2000, left, right, tzinfo=UTC)
        except ValueError as exc:
            raise ValidationError(
                f"{register.key}: invalid month/day {left:02d}-{right:02d}"
            ) from exc
        return f"{left:02d}-{right:02d}"
    if not 0 <= left <= 7 or not 0 <= right <= 59:
        raise ValidationError(
            f"{register.key}: weekday must be 0..7 and second 0..59"
        )
    return f"{left}:{right:02d}"


def _normalize_number(register: RegisterDef, value: Any) -> int | float:
    """Enforce numeric range, special values, step, and scale precision."""
    number = _coerce_number(value, key=register.key)
    is_extra = any(
        math.isclose(number, extra, abs_tol=1e-9) for extra in register.extra_values
    )
    if not is_extra:
        if register.minimum is not None and number < register.minimum - 1e-9:
            raise ValidationError(
                f"{register.key}: {number:g} is below minimum {register.minimum:g}"
            )
        if register.maximum is not None and number > register.maximum + 1e-9:
            raise ValidationError(
                f"{register.key}: {number:g} is above maximum {register.maximum:g}"
            )
        if register.step is not None:
            quotient = (number - (register.minimum or 0.0)) / register.step
            if not math.isclose(quotient, round(quotient), abs_tol=1e-7):
                raise ValidationError(
                    f"{register.key}: {number:g} does not follow step size "
                    f"{register.step:g}"
                )
    return _format_scaled(number, register.scale)


def normalize_value(register: RegisterDef, value: Any) -> JSONScalar:
    """Validate and canonicalize a value using the definition's codec."""
    if register.codec == "enum":
        return _normalize_enum(register, value)
    if register.codec in {"bool", "standby_command"}:
        return _coerce_bool(value, key=register.key)
    if register.codec.startswith("packed_"):
        return _normalize_packed(register, value)
    numeric = {
        "u16", "s16", "scaled_u16", "scaled_s16", "flow_cwl325", "pwm_with_zero"
    }
    if register.codec in numeric:
        return _normalize_number(register, value)
    readonly = {"software_version", "hardware_version", "serial_bcd12", "u32", "raw_words"}
    if register.codec in readonly:
        raise RegisterError(f"{register.key}: read-only value")
    raise RuntimeError(f"unknown codec {register.codec!r} for {register.key}")


def encode_value(register: RegisterDef, value: Any) -> list[int]:
    """Encode a canonicalized engineering value into Modbus words."""
    normalized = normalize_value(register, value)
    if register.codec == "enum":
        assert isinstance(normalized, str)
        return [enum_reverse(register)[slug(normalized)]]
    if register.codec == "bool":
        return [1 if normalized else 0]
    if register.codec == "standby_command":
        return [1 if normalized else 2]
    if register.codec.startswith("packed_"):
        separator = "-" if register.codec == "packed_month_day" else ":"
        left, right = str(normalized).split(separator, 1)
        return [(int(left) << 8) | int(right)]
    if not isinstance(normalized, (int, float)) or isinstance(normalized, bool):
        raise RegisterError(f"{register.key}: normalized numeric value is invalid")
    raw = int(round(float(normalized)))
    if register.codec in {"scaled_u16", "scaled_s16"}:
        raw = int(round(float(normalized) / register.scale))
    if register.codec in {"s16", "scaled_s16"}:
        if not -32768 <= raw <= 32767:
            raise ValidationError(f"signed 16-bit value out of range: {raw}")
        return [raw & 0xFFFF]
    if not 0 <= raw <= 0xFFFF:
        raise ValidationError(
            f"{register.key}: encoded value {raw} is outside unsigned 16-bit range"
        )
    return [raw]


def decode_value(register: RegisterDef, words: Sequence[int]) -> JSONValue:
    """Decode Modbus words into a JSON-compatible engineering value."""
    if len(words) != register.count:
        raise ValueError(
            f"{register.key}: expected {register.count} words, got {len(words)}"
        )
    raw = int(words[0])
    if register.codec == "enum":
        assert register.enum is not None
        return register.enum.get(raw, f"unknown_{raw}")
    if register.codec == "bool":
        return bool(raw)
    if register.codec == "standby_command":
        return False if raw == 0 else True if raw == 1 else f"unknown_{raw}"
    if register.codec in {"u16", "flow_cwl325", "pwm_with_zero"}:
        return raw
    signed = raw - 0x10000 if raw & 0x8000 else raw
    if register.codec == "s16":
        return signed
    if register.codec == "scaled_u16":
        return _format_scaled(raw * register.scale, register.scale)
    if register.codec == "scaled_s16":
        return _format_scaled(signed * register.scale, register.scale)
    if register.codec == "u32":
        return (int(words[0]) << 16) | int(words[1])
    if register.codec == "serial_bcd12":
        return "".join(
            "".join(str((int(word) >> shift) & 0xF) for shift in (12, 8, 4, 0))
            for word in words
        )
    if register.codec == "software_version":
        type_byte = (raw >> 8) & 0xFF
        type_char = chr(type_byte) if 32 <= type_byte <= 126 else f"0x{type_byte:02X}"
        return (
            f"{type_char}{raw & 0xFF}.{(int(words[1]) >> 8) & 0xFF:02d}."
            f"{int(words[1]) & 0xFF:02d}.{int(words[2]):04d}"
        )
    if register.codec == "hardware_version":
        return f"H{(raw >> 8) & 0xFF}.{raw & 0xFF}"
    if register.codec == "packed_hm":
        left, right = (raw >> 8) & 0xFF, raw & 0xFF
        return f"{left:02d}:{right:02d}" if left <= 23 and right <= 59 else f"invalid_0x{raw:04X}"
    if register.codec == "packed_month_day":
        return f"{(raw >> 8) & 0xFF:02d}-{raw & 0xFF:02d}"
    if register.codec == "packed_weekday_second":
        return f"{(raw >> 8) & 0xFF}:{raw & 0xFF:02d}"
    if register.codec == "raw_words":
        return [int(word) for word in words]
    raise RuntimeError(f"unknown codec {register.codec!r} for {register.key}")
