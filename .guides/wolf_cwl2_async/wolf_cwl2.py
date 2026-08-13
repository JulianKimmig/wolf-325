#!/usr/bin/env python3
"""Async controller for a WOLF CWL-2-325 through a Modbus TCP/RTU gateway.

The CWL-2-325 uses the Brink UWA2-B/UWA2-E Modbus register map.  This file can
be used as a library or as a small long-running daemon/CLI.

Python: 3.11+
Dependency: pymodbus 3.14.x

Important behavior:
* Input and holding registers are polled continuously in non-overlapping blocks.
* Every Modbus operation is serialized because one pymodbus client must not be
  called concurrently.
* Desired values are stored atomically in a local JSON configuration file.
* Desired values are force-written at startup and after a reconnect, which is
  especially important for remote-control registers 8000-8003.
* Profiles are partial JSON configurations and may extend other profiles.
* One-shot reset registers and communication registers are never restored
  automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import copy
import inspect
import json
import logging
import math
import os
import re
import signal
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, TypeAlias

from pymodbus import FramerType
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

LOGGER = logging.getLogger("wolf_cwl2")

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
TableName: TypeAlias = Literal["input", "holding"]
PollTier: TypeAlias = Literal["fast", "slow", "static", "never"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WolfError(Exception):
    """Base exception for this module."""


class ConfigError(WolfError):
    """Invalid or inaccessible configuration."""


class ProfileError(WolfError):
    """Invalid profile or profile dependency."""


class RegisterError(WolfError):
    """Invalid register name/value or unsupported write."""


class ValidationError(RegisterError):
    """A value violates a register or cross-register constraint."""


class CommunicationError(WolfError):
    """No usable connection to the Modbus gateway/device."""


class RemoteModbusError(CommunicationError):
    """The remote Modbus device returned an exception response."""


class VerificationError(RegisterError):
    """A write completed but the read-back value did not match."""


class BulkWriteError(RegisterError):
    """One or more writes from a bulk operation failed."""

    def __init__(
        self, message: str, results: Mapping[str, Any], errors: Mapping[str, str]
    ) -> None:
        super().__init__(message)
        self.results = dict(results)
        self.errors = dict(errors)


# ---------------------------------------------------------------------------
# Register codecs and metadata
# ---------------------------------------------------------------------------


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _coerce_bool(value: Any, *, key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = _slug(value)
        if text in {"1", "true", "yes", "on", "enabled", "enable"}:
            return True
        if text in {"0", "false", "no", "off", "disabled", "disable"}:
            return False
    raise ValidationError(f"{key}: expected a boolean, got {value!r}")


def _coerce_number(value: Any, *, key: str) -> float:
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


def _signed_word(raw: int) -> int:
    return raw - 0x10000 if raw & 0x8000 else raw


def _encode_signed_word(value: int) -> int:
    if not -32768 <= value <= 32767:
        raise ValidationError(f"signed 16-bit value out of range: {value}")
    return value & 0xFFFF


def _format_scaled(value: float, scale: float) -> int | float:
    if math.isclose(scale, 1.0):
        return int(round(value))
    decimals = max(0, int(round(-math.log10(scale)))) if scale < 1 else 6
    return round(value, decimals)


def _bcd_nibbles(word: int) -> str:
    parts: list[str] = []
    for shift in (12, 8, 4, 0):
        nibble = (word >> shift) & 0xF
        parts.append(str(nibble) if nibble <= 9 else f"{nibble:X}")
    return "".join(parts)


@dataclass(frozen=True, slots=True)
class RegisterDef:
    """Description and codec for one logical Modbus value."""

    key: str
    address: int
    table: TableName
    description: str
    codec: str = "u16"
    count: int = 1
    scale: float = 1.0
    unit: str | None = None
    enum: Mapping[int, str] | None = None
    enum_aliases: Mapping[str, str] = field(default_factory=dict)
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    extra_values: tuple[float, ...] = ()
    writable: bool = False
    restorable: bool = False
    dangerous: bool = False
    one_shot: bool = False
    optional: bool = False
    poll: PollTier = "slow"

    def _enum_reverse(self) -> dict[str, int]:
        reverse = {_slug(label): raw for raw, label in (self.enum or {}).items()}
        for alias, canonical in self.enum_aliases.items():
            canonical_slug = _slug(canonical)
            if canonical_slug not in reverse:
                raise RuntimeError(
                    f"bad enum alias for {self.key}: {alias} -> {canonical}"
                )
            reverse[_slug(alias)] = reverse[canonical_slug]
        return reverse

    def normalize(self, value: Any) -> JSONScalar:
        """Validate and convert a user value to a canonical JSON scalar."""
        if self.codec == "enum":
            assert self.enum is not None
            if isinstance(value, bool):
                raise ValidationError(f"{self.key}: boolean is not an enum value")
            if isinstance(value, int):
                if value not in self.enum:
                    raise ValidationError(
                        f"{self.key}: {value} is not valid; allowed raw values: {sorted(self.enum)}"
                    )
                return self.enum[value]
            if isinstance(value, str):
                reverse = self._enum_reverse()
                candidate = _slug(value)
                if candidate in reverse:
                    return self.enum[reverse[candidate]]
                if value.strip().lstrip("-").isdigit():
                    return self.normalize(int(value))
                allowed = ", ".join(self.enum.values())
                raise ValidationError(
                    f"{self.key}: expected one of [{allowed}], got {value!r}"
                )
            raise ValidationError(f"{self.key}: invalid enum value {value!r}")

        if self.codec in {"bool", "standby_command"}:
            return _coerce_bool(value, key=self.key)

        if self.codec == "packed_hm":
            if isinstance(value, str) and re.fullmatch(r"\d{1,2}:\d{2}", value.strip()):
                hour_s, minute_s = value.strip().split(":", 1)
                hour, minute = int(hour_s), int(minute_s)
            elif isinstance(value, Mapping):
                hour, minute = int(value["hour"]), int(value["minute"])
            elif (
                isinstance(value, Sequence)
                and not isinstance(value, (str, bytes))
                and len(value) == 2
            ):
                hour, minute = int(value[0]), int(value[1])
            else:
                raise ValidationError(
                    f"{self.key}: expected HH:MM, {{hour, minute}}, or [hour, minute]"
                )
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValidationError(
                    f"{self.key}: invalid time {hour:02d}:{minute:02d}"
                )
            return f"{hour:02d}:{minute:02d}"

        if self.codec == "packed_month_day":
            if isinstance(value, str) and re.fullmatch(
                r"\d{1,2}-\d{1,2}", value.strip()
            ):
                month_s, day_s = value.strip().split("-", 1)
                month, day = int(month_s), int(day_s)
            elif isinstance(value, Mapping):
                month, day = int(value["month"]), int(value["day"])
            elif (
                isinstance(value, Sequence)
                and not isinstance(value, (str, bytes))
                and len(value) == 2
            ):
                month, day = int(value[0]), int(value[1])
            else:
                raise ValidationError(
                    f"{self.key}: expected MM-DD, {{month, day}}, or [month, day]"
                )
            try:
                datetime(2000, month, day, tzinfo=UTC)
            except ValueError as exc:
                raise ValidationError(
                    f"{self.key}: invalid month/day {month:02d}-{day:02d}"
                ) from exc
            return f"{month:02d}-{day:02d}"

        if self.codec == "packed_weekday_second":
            if isinstance(value, Mapping):
                weekday, second = int(value["weekday"]), int(value["second"])
            elif (
                isinstance(value, Sequence)
                and not isinstance(value, (str, bytes))
                and len(value) == 2
            ):
                weekday, second = int(value[0]), int(value[1])
            elif isinstance(value, str) and re.fullmatch(r"\d:\d{1,2}", value.strip()):
                weekday_s, second_s = value.strip().split(":", 1)
                weekday, second = int(weekday_s), int(second_s)
            else:
                raise ValidationError(
                    f"{self.key}: expected {{weekday, second}}, [weekday, second], or weekday:second"
                )
            if not 0 <= weekday <= 7 or not 0 <= second <= 59:
                raise ValidationError(
                    f"{self.key}: weekday must be 0..7 and second 0..59"
                )
            return f"{weekday}:{second:02d}"

        if self.codec in {
            "u16",
            "s16",
            "scaled_u16",
            "scaled_s16",
            "flow_cwl325",
            "pwm_with_zero",
        }:
            number = _coerce_number(value, key=self.key)
            is_extra = any(
                math.isclose(number, extra, abs_tol=1e-9) for extra in self.extra_values
            )
            if not is_extra:
                if self.minimum is not None and number < self.minimum - 1e-9:
                    raise ValidationError(
                        f"{self.key}: {number:g} is below minimum {self.minimum:g}"
                    )
                if self.maximum is not None and number > self.maximum + 1e-9:
                    raise ValidationError(
                        f"{self.key}: {number:g} is above maximum {self.maximum:g}"
                    )
                if self.step is not None:
                    origin = self.minimum or 0.0
                    quotient = (number - origin) / self.step
                    if not math.isclose(quotient, round(quotient), abs_tol=1e-7):
                        raise ValidationError(
                            f"{self.key}: {number:g} does not follow step size {self.step:g}"
                        )
            scaled = _format_scaled(number, self.scale)
            return scaled

        if self.codec in {
            "software_version",
            "hardware_version",
            "serial_bcd12",
            "u32",
            "raw_words",
        }:
            if self.writable:
                raise RegisterError(f"{self.key}: codec {self.codec} is read-only")
            raise RegisterError(f"{self.key}: read-only value")

        raise RuntimeError(f"unknown codec {self.codec!r} for {self.key}")

    def encode(self, value: Any) -> list[int]:
        """Encode a user value into one or more 16-bit words."""
        normalized = self.normalize(value)

        if self.codec == "enum":
            reverse = self._enum_reverse()
            assert isinstance(normalized, str)
            return [reverse[_slug(normalized)]]
        if self.codec == "bool":
            return [1 if normalized else 0]
        if self.codec == "standby_command":
            # The write command is 1=standby, 2=normal; read-back is 0/1 state.
            return [1 if normalized else 2]
        if self.codec == "packed_hm":
            hour_s, minute_s = str(normalized).split(":", 1)
            return [(int(hour_s) << 8) | int(minute_s)]
        if self.codec == "packed_month_day":
            month_s, day_s = str(normalized).split("-", 1)
            return [(int(month_s) << 8) | int(day_s)]
        if self.codec == "packed_weekday_second":
            weekday_s, second_s = str(normalized).split(":", 1)
            return [(int(weekday_s) << 8) | int(second_s)]

        if self.codec in {"u16", "s16", "flow_cwl325", "pwm_with_zero"}:
            if not isinstance(normalized, (int, float)) or isinstance(normalized, bool):
                raise RegisterError(f"{self.key}: normalized numeric value is invalid")
            raw = int(round(float(normalized)))
        elif self.codec in {"scaled_u16", "scaled_s16"}:
            if not isinstance(normalized, (int, float)) or isinstance(normalized, bool):
                raise RegisterError(f"{self.key}: normalized numeric value is invalid")
            raw = int(round(float(normalized) / self.scale))
        else:
            raise RegisterError(f"{self.key}: codec {self.codec} cannot be written")

        if self.codec in {"s16", "scaled_s16"}:
            return [_encode_signed_word(raw)]
        if not 0 <= raw <= 0xFFFF:
            raise ValidationError(
                f"{self.key}: encoded value {raw} is outside unsigned 16-bit range"
            )
        return [raw]

    def decode(self, words: Sequence[int]) -> JSONValue:
        """Decode register words into a JSON-compatible engineering value."""
        if len(words) != self.count:
            raise ValueError(
                f"{self.key}: expected {self.count} words, got {len(words)}"
            )
        raw = int(words[0])

        if self.codec == "enum":
            assert self.enum is not None
            return self.enum.get(raw, f"unknown_{raw}")
        if self.codec == "bool":
            return bool(raw)
        if self.codec == "standby_command":
            if raw == 0:
                return False
            if raw == 1:
                return True
            return f"unknown_{raw}"
        if self.codec == "u16" or self.codec in {"flow_cwl325", "pwm_with_zero"}:
            return raw
        if self.codec == "s16":
            return _signed_word(raw)
        if self.codec == "scaled_u16":
            return _format_scaled(raw * self.scale, self.scale)
        if self.codec == "scaled_s16":
            return _format_scaled(_signed_word(raw) * self.scale, self.scale)
        if self.codec == "u32":
            return (int(words[0]) << 16) | int(words[1])
        if self.codec == "serial_bcd12":
            return "".join(_bcd_nibbles(int(word)) for word in words)
        if self.codec == "software_version":
            first = int(words[0])
            type_byte = (first >> 8) & 0xFF
            type_char = (
                chr(type_byte) if 32 <= type_byte <= 126 else f"0x{type_byte:02X}"
            )
            major = first & 0xFF
            minor = (int(words[1]) >> 8) & 0xFF
            fix = int(words[1]) & 0xFF
            build = int(words[2])
            return f"{type_char}{major}.{minor:02d}.{fix:02d}.{build:04d}"
        if self.codec == "hardware_version":
            major = (raw >> 8) & 0xFF
            minor = raw & 0xFF
            return f"H{major}.{minor}"
        if self.codec == "packed_hm":
            hour, minute = (raw >> 8) & 0xFF, raw & 0xFF
            return (
                f"{hour:02d}:{minute:02d}"
                if hour <= 23 and minute <= 59
                else f"invalid_0x{raw:04X}"
            )
        if self.codec == "packed_month_day":
            month, day = (raw >> 8) & 0xFF, raw & 0xFF
            return f"{month:02d}-{day:02d}"
        if self.codec == "packed_weekday_second":
            weekday, second = (raw >> 8) & 0xFF, raw & 0xFF
            return f"{weekday}:{second:02d}"
        if self.codec == "raw_words":
            return [int(word) for word in words]
        raise RuntimeError(f"unknown codec {self.codec!r} for {self.key}")

    def raw_json(self, words: Sequence[int]) -> JSONValue:
        return int(words[0]) if len(words) == 1 else [int(word) for word in words]


# Enumerations use stable, lower-case names that are convenient in JSON/profile files.
ACTIVE_FUNCTION: Final = {
    0: "standby",
    1: "bootloader",
    2: "non_blocking_error",
    3: "blocking_error",
    4: "manual",
    5: "holiday",
    6: "night_ventilation",
    7: "party",
    8: "bypass_boost",
    9: "normal_boost",
    10: "auto_co2",
    11: "auto_ebus",
    12: "auto_modbus",
    13: "auto_portal",
    14: "auto_local_network",
}
FAN_CONTROL_TYPE: Final = {
    0: "initializing",
    1: "constant_flow",
    2: "constant_pwm",
    3: "off",
    4: "error",
    5: "mass_balance",
    6: "standby",
}
VENTILATION_MODE: Final = {0: "holiday", 1: "low", 2: "normal", 3: "high", 4: "auto"}
REMOTE_LEVEL: Final = {0: "holiday", 1: "low", 2: "normal", 3: "high"}
FAN_STATUS: Final = {
    2: "no_communication",
    3: "idle",
    4: "running",
    5: "blocked",
    6: "fan_error",
}
BYPASS_STATUS: Final = {
    0: "initializing",
    1: "opening",
    2: "closing",
    3: "open",
    4: "closed",
}
PREHEATER_STATUS: Final = {
    0: "initializing",
    1: "inactive",
    2: "active",
    3: "test_mode",
}
FROST_STATUS: Final = {
    0: "not_initialized",
    1: "power_up_delay",
    2: "no_frost",
    3: "no_frost_delay",
    4: "frost_control_start_delay",
    5: "wait_for_icing",
    6: "ice_detected_delay",
    7: "heating",
    8: "wait_for_free_heater",
    9: "fan_control_start_delay",
    10: "fan_control_wait_delay",
    11: "fan_control",
    12: "fan_off_delay",
    13: "fan_off",
    14: "fan_restarting",
    15: "error",
    16: "test_mode",
}
FLOW_POSITION: Final = {0: "holiday", 1: "low", 2: "normal", 3: "high", 255: "invalid"}
EBUS_POWER_STATUS: Final = {
    0: "power_up",
    1: "initialize_power",
    2: "power_off",
    3: "power_on",
    4: "wait_for_power_off",
    5: "slave_power_off",
}
CO2_STATUS: Final = {
    0: "error",
    1: "not_initialized",
    2: "idle",
    3: "warming_up",
    4: "running",
    5: "calibrating",
    6: "self_test",
}
FAN_INPUT_FUNCTION: Final = {
    0: "fan_off",
    1: "absolute_minimum_flow",
    2: "preset_1",
    3: "preset_2",
    4: "preset_3",
    5: "physical_switch",
    6: "absolute_maximum_flow",
    7: "unchanged",
}


def _reg(
    key: str,
    address: int,
    table: TableName,
    description: str,
    **kwargs: Any,
) -> RegisterDef:
    return RegisterDef(
        key=key, address=address, table=table, description=description, **kwargs
    )


def _input_registers() -> list[RegisterDef]:
    regs: list[RegisterDef] = [
        _reg(
            "base_software_version",
            4000,
            "input",
            "UWA2-B software version",
            codec="software_version",
            count=3,
            poll="static",
        ),
        _reg(
            "base_hardware_version",
            4003,
            "input",
            "UWA2-B hardware version",
            codec="hardware_version",
            poll="static",
        ),
        _reg("appliance_type", 4004, "input", "Internal appliance type", poll="static"),
        _reg(
            "base_dipswitch_value",
            4005,
            "input",
            "UWA2-B DIP-switch value",
            poll="static",
        ),
        _reg(
            "serial_number",
            4010,
            "input",
            "12-digit appliance serial number",
            codec="serial_bcd12",
            count=3,
            poll="static",
        ),
        _reg(
            "active_function",
            4020,
            "input",
            "Current appliance function",
            codec="enum",
            enum=ACTIVE_FUNCTION,
            poll="fast",
        ),
        _reg(
            "fan_control_type",
            4021,
            "input",
            "Active fan-control method",
            codec="enum",
            enum=FAN_CONTROL_TYPE,
            poll="fast",
        ),
        _reg(
            "ventilation_mode",
            4022,
            "input",
            "Current ventilation level",
            codec="enum",
            enum=VENTILATION_MODE,
            poll="fast",
        ),
        _reg(
            "supply_pressure_pa",
            4023,
            "input",
            "Current supply pressure",
            codec="scaled_s16",
            scale=0.1,
            unit="Pa",
            poll="fast",
        ),
        _reg(
            "exhaust_pressure_pa",
            4024,
            "input",
            "Current exhaust pressure",
            codec="scaled_s16",
            scale=0.1,
            unit="Pa",
            poll="fast",
        ),
        _reg(
            "supply_fan_status",
            4030,
            "input",
            "Supply fan status",
            codec="enum",
            enum=FAN_STATUS,
            poll="fast",
        ),
        _reg(
            "supply_airflow_setpoint_m3h",
            4031,
            "input",
            "Supply airflow setpoint",
            unit="m³/h",
            poll="fast",
        ),
        _reg(
            "supply_airflow_actual_m3h",
            4032,
            "input",
            "Actual supply airflow",
            unit="m³/h",
            poll="fast",
        ),
        _reg(
            "supply_mass_flow_actual_kgh",
            4033,
            "input",
            "Actual supply mass flow",
            unit="kg/h",
            poll="fast",
        ),
        _reg(
            "supply_fan_speed_rpm",
            4034,
            "input",
            "Supply fan speed",
            unit="rpm",
            poll="fast",
        ),
        _reg(
            "supply_anemometer_speed_rpm",
            4035,
            "input",
            "Supply anemometer speed",
            unit="rpm",
            poll="fast",
        ),
        _reg(
            "supply_temperature_c",
            4036,
            "input",
            "Supply air temperature",
            codec="scaled_s16",
            scale=0.1,
            unit="°C",
            poll="fast",
        ),
        _reg(
            "supply_relative_humidity_pct",
            4037,
            "input",
            "Supply relative humidity",
            codec="scaled_u16",
            scale=0.1,
            unit="%",
            poll="fast",
            optional=True,
        ),
        _reg(
            "exhaust_fan_status",
            4040,
            "input",
            "Exhaust fan status",
            codec="enum",
            enum=FAN_STATUS,
            poll="fast",
        ),
        _reg(
            "exhaust_airflow_setpoint_m3h",
            4041,
            "input",
            "Exhaust airflow setpoint",
            unit="m³/h",
            poll="fast",
        ),
        _reg(
            "exhaust_airflow_actual_m3h",
            4042,
            "input",
            "Actual exhaust airflow",
            unit="m³/h",
            poll="fast",
        ),
        _reg(
            "exhaust_mass_flow_actual_kgh",
            4043,
            "input",
            "Actual exhaust mass flow",
            unit="kg/h",
            poll="fast",
        ),
        _reg(
            "exhaust_fan_speed_rpm",
            4044,
            "input",
            "Exhaust fan speed",
            unit="rpm",
            poll="fast",
        ),
        _reg(
            "exhaust_anemometer_speed_rpm",
            4045,
            "input",
            "Exhaust anemometer speed",
            unit="rpm",
            poll="fast",
        ),
        _reg(
            "exhaust_temperature_c",
            4046,
            "input",
            "Exhaust air temperature",
            codec="scaled_s16",
            scale=0.1,
            unit="°C",
            poll="fast",
        ),
        _reg(
            "exhaust_relative_humidity_pct",
            4047,
            "input",
            "Exhaust relative humidity",
            codec="scaled_u16",
            scale=0.1,
            unit="%",
            poll="fast",
            optional=True,
        ),
        _reg(
            "bypass_status",
            4050,
            "input",
            "Bypass state",
            codec="enum",
            enum=BYPASS_STATUS,
            poll="fast",
        ),
        _reg(
            "bypass_step_position",
            4051,
            "input",
            "Bypass motor position relative to zero",
            poll="fast",
        ),
        _reg(
            "preheater_status",
            4060,
            "input",
            "Preheater state",
            codec="enum",
            enum=PREHEATER_STATUS,
            poll="fast",
        ),
        _reg(
            "preheater_capacity_pct",
            4061,
            "input",
            "Preheater output",
            unit="%",
            poll="fast",
        ),
        _reg(
            "frost_status",
            4070,
            "input",
            "Frost-protection state",
            codec="enum",
            enum=FROST_STATUS,
            poll="fast",
        ),
        _reg(
            "frost_heater_power_pct",
            4071,
            "input",
            "Frost heater output",
            unit="%",
            poll="fast",
        ),
        _reg(
            "frost_fan_reduction_pct",
            4072,
            "input",
            "Fan reduction by frost control",
            unit="%",
            poll="fast",
        ),
        _reg(
            "physical_switch_position",
            4080,
            "input",
            "Physical four-position switch",
            codec="enum",
            enum=FLOW_POSITION,
            poll="fast",
        ),
        _reg(
            "ntc1_temperature_c",
            4081,
            "input",
            "NTC1 temperature",
            codec="scaled_s16",
            scale=0.1,
            unit="°C",
            poll="fast",
            optional=True,
        ),
        _reg(
            "ntc2_temperature_c",
            4082,
            "input",
            "NTC2 temperature",
            codec="scaled_s16",
            scale=0.1,
            unit="°C",
            poll="fast",
            optional=True,
        ),
        _reg(
            "rht_humidity_pct",
            4083,
            "input",
            "RHT sensor humidity",
            codec="scaled_u16",
            scale=0.1,
            unit="%",
            poll="fast",
            optional=True,
        ),
        _reg(
            "signal_output_state",
            4090,
            "input",
            "24 V signal output state",
            codec="enum",
            enum={0: "off", 1: "on"},
            poll="fast",
        ),
        _reg(
            "filter_status",
            4100,
            "input",
            "Filter warning state",
            codec="enum",
            enum={0: "clean", 1: "dirty"},
            poll="fast",
        ),
        _reg(
            "ebus_power_status",
            4101,
            "input",
            "eBUS power state",
            codec="enum",
            enum=EBUS_POWER_STATUS,
            poll="fast",
        ),
        _reg(
            "appliance_time",
            4110,
            "input",
            "Appliance clock",
            codec="packed_hm",
            poll="slow",
        ),
        _reg(
            "appliance_date_raw",
            4111,
            "input",
            "Appliance date words (manual encoding is ambiguous)",
            codec="raw_words",
            count=2,
            poll="slow",
        ),
        _reg(
            "operating_time_hours",
            4113,
            "input",
            "Total operating time",
            codec="u32",
            count=2,
            unit="h",
            poll="slow",
        ),
        _reg(
            "filter_runtime_hours",
            4115,
            "input",
            "Operating hours since filter reset",
            unit="h",
            poll="slow",
        ),
        _reg(
            "filter_air_volume_counter",
            4116,
            "input",
            "Air-volume counter since filter reset",
            codec="u32",
            count=2,
            unit="m³",
            poll="slow",
        ),
        _reg(
            "total_air_volume_counter",
            4118,
            "input",
            "Total air-volume counter",
            codec="u32",
            count=2,
            unit="m³",
            poll="slow",
        ),
        _reg(
            "geo_heat_exchanger_status",
            4150,
            "input",
            "Ground heat exchanger state",
            codec="enum",
            enum={0: "open_low", 1: "closed", 2: "open_high"},
            optional=True,
            poll="fast",
        ),
    ]

    for sensor in range(1, 5):
        base = 4200 + (sensor - 1) * 2
        regs.extend(
            [
                _reg(
                    f"co2_sensor_{sensor}_status",
                    base,
                    "input",
                    f"CO₂ sensor {sensor} state",
                    codec="enum",
                    enum=CO2_STATUS,
                    optional=True,
                    poll="fast",
                ),
                _reg(
                    f"co2_sensor_{sensor}_ppm",
                    base + 1,
                    "input",
                    f"CO₂ sensor {sensor} value",
                    unit="ppm",
                    optional=True,
                    poll="fast",
                ),
            ]
        )

    regs.extend(
        [
            _reg(
                "ui_software_version",
                4400,
                "input",
                "UI module software version",
                codec="software_version",
                count=3,
                optional=True,
                poll="static",
            ),
            _reg(
                "ui_hardware_version",
                4403,
                "input",
                "UI module hardware version",
                codec="hardware_version",
                optional=True,
                poll="static",
            ),
            _reg(
                "ui_device_type",
                4404,
                "input",
                "UI module device type",
                optional=True,
                poll="static",
            ),
            _reg(
                "ui_dipswitch_value",
                4405,
                "input",
                "UI module DIP-switch value",
                optional=True,
                poll="static",
            ),
            _reg(
                "ui_language_data_version",
                4410,
                "input",
                "UI language data version",
                codec="software_version",
                count=3,
                optional=True,
                poll="static",
            ),
            _reg(
                "ui_secondary_software_version",
                4413,
                "input",
                "UI secondary software version",
                codec="software_version",
                count=3,
                optional=True,
                poll="static",
            ),
            _reg(
                "local_ui_switch",
                4420,
                "input",
                "Level selected on local UI",
                optional=True,
                poll="slow",
            ),
            _reg(
                "local_ui_button",
                4421,
                "input",
                "Local UI button value",
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_software_version",
                4500,
                "input",
                "UWA2-E software version",
                codec="software_version",
                count=3,
                optional=True,
                poll="static",
            ),
            _reg(
                "extension_hardware_version",
                4503,
                "input",
                "UWA2-E hardware version",
                codec="hardware_version",
                optional=True,
                poll="static",
            ),
            _reg(
                "extension_device_type",
                4504,
                "input",
                "UWA2-E device type",
                optional=True,
                poll="static",
            ),
            _reg(
                "extension_dipswitch_value",
                4505,
                "input",
                "UWA2-E DIP-switch value",
                optional=True,
                poll="static",
            ),
            _reg(
                "extension_ntc_temperature_c",
                4520,
                "input",
                "UWA2-E NTC temperature",
                codec="scaled_s16",
                scale=0.1,
                unit="°C",
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_contact_1",
                4521,
                "input",
                "UWA2-E contact 1",
                codec="enum",
                enum={0: "open", 1: "closed"},
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_contact_2",
                4522,
                "input",
                "UWA2-E contact 2",
                codec="enum",
                enum={0: "open", 1: "closed"},
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_analog_input_1_v",
                4523,
                "input",
                "UWA2-E analogue input 1",
                codec="scaled_u16",
                scale=0.1,
                unit="V",
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_analog_input_2_v",
                4524,
                "input",
                "UWA2-E analogue input 2",
                codec="scaled_u16",
                scale=0.1,
                unit="V",
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_relay_output_1",
                4541,
                "input",
                "UWA2-E relay output 1",
                codec="enum",
                enum={0: "off", 1: "on"},
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_relay_output_2",
                4542,
                "input",
                "UWA2-E relay output 2",
                codec="enum",
                enum={0: "off", 1: "on"},
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_analog_output_1_v",
                4543,
                "input",
                "UWA2-E analogue output 1",
                codec="scaled_u16",
                scale=0.1,
                unit="V",
                optional=True,
                poll="slow",
            ),
            _reg(
                "extension_analog_output_2_v",
                4544,
                "input",
                "UWA2-E analogue output 2",
                codec="scaled_u16",
                scale=0.1,
                unit="V",
                optional=True,
                poll="slow",
            ),
        ]
    )
    return regs


def _holding_registers() -> list[RegisterDef]:
    flow_kwargs = dict(
        codec="flow_cwl325",
        minimum=50,
        maximum=325,
        step=5,
        unit="m³/h",
        writable=True,
        restorable=True,
        poll="slow",
    )
    pwm_kwargs = dict(
        codec="pwm_with_zero",
        minimum=15,
        maximum=100,
        step=1,
        extra_values=(0,),
        unit="%",
        writable=True,
        restorable=True,
        poll="slow",
    )

    regs: list[RegisterDef] = [
        _reg(
            "flow_preset_holiday_m3h",
            6000,
            "holding",
            "Airflow preset 0 / holiday",
            extra_values=(0,),
            **flow_kwargs,
        ),
        _reg(
            "flow_preset_low_m3h",
            6001,
            "holding",
            "Airflow preset 1 / low",
            **flow_kwargs,
        ),
        _reg(
            "flow_preset_normal_m3h",
            6002,
            "holding",
            "Airflow preset 2 / normal",
            **flow_kwargs,
        ),
        _reg(
            "flow_preset_high_m3h",
            6003,
            "holding",
            "Airflow preset 3 / high",
            **flow_kwargs,
        ),
        _reg(
            "pwm_supply_holiday_pct",
            6010,
            "holding",
            "Supply PWM preset 0",
            **pwm_kwargs,
        ),
        _reg(
            "pwm_exhaust_holiday_pct",
            6011,
            "holding",
            "Exhaust PWM preset 0",
            **pwm_kwargs,
        ),
        _reg(
            "pwm_supply_low_pct", 6012, "holding", "Supply PWM preset 1", **pwm_kwargs
        ),
        _reg(
            "pwm_exhaust_low_pct", 6013, "holding", "Exhaust PWM preset 1", **pwm_kwargs
        ),
        _reg(
            "pwm_supply_normal_pct",
            6014,
            "holding",
            "Supply PWM preset 2",
            **pwm_kwargs,
        ),
        _reg(
            "pwm_exhaust_normal_pct",
            6015,
            "holding",
            "Exhaust PWM preset 2",
            **pwm_kwargs,
        ),
        _reg(
            "pwm_supply_high_pct", 6016, "holding", "Supply PWM preset 3", **pwm_kwargs
        ),
        _reg(
            "pwm_exhaust_high_pct",
            6017,
            "holding",
            "Exhaust PWM preset 3",
            **pwm_kwargs,
        ),
        _reg(
            "flow_control_method",
            6030,
            "holding",
            "Fan control method",
            codec="enum",
            enum={0: "constant_pwm", 1: "constant_flow", 2: "constant_mass_flow"},
            writable=True,
            restorable=True,
        ),
        _reg(
            "switch_default_position",
            6031,
            "holding",
            "Default physical switch position",
            minimum=0,
            maximum=1,
            writable=True,
            restorable=True,
        ),
        _reg(
            "use_display_as_switch",
            6032,
            "holding",
            "Use display as level switch",
            codec="bool",
            writable=True,
            restorable=True,
        ),
        _reg(
            "imbalance_allowed",
            6033,
            "holding",
            "Allow supply/exhaust imbalance",
            codec="bool",
            writable=True,
            restorable=True,
        ),
        _reg(
            "imbalance_pct",
            6034,
            "holding",
            "Supply airflow increase relative to exhaust",
            minimum=0,
            maximum=20,
            step=1,
            unit="%",
            writable=True,
            restorable=True,
        ),
        _reg(
            "supply_imbalance_offset_pct",
            6035,
            "holding",
            "Supply imbalance correction",
            codec="s16",
            minimum=-15,
            maximum=15,
            step=1,
            unit="%",
            writable=True,
            restorable=True,
        ),
        _reg(
            "exhaust_imbalance_offset_pct",
            6036,
            "holding",
            "Exhaust imbalance correction",
            codec="s16",
            minimum=-15,
            maximum=15,
            step=1,
            unit="%",
            writable=True,
            restorable=True,
        ),
        _reg(
            "bypass_mode",
            6100,
            "holding",
            "Bypass mode",
            codec="enum",
            enum={0: "automatic", 1: "closed", 2: "open"},
            enum_aliases={"auto": "automatic"},
            writable=True,
            restorable=True,
        ),
        _reg(
            "bypass_indoor_threshold_c",
            6101,
            "holding",
            "Indoor temperature threshold for bypass",
            codec="scaled_s16",
            scale=0.1,
            minimum=15.0,
            maximum=35.0,
            step=0.5,
            unit="°C",
            writable=True,
            restorable=True,
        ),
        _reg(
            "bypass_outdoor_threshold_c",
            6102,
            "holding",
            "Outdoor temperature threshold for bypass",
            codec="scaled_s16",
            scale=0.1,
            minimum=7.0,
            maximum=15.0,
            step=0.5,
            unit="°C",
            writable=True,
            restorable=True,
        ),
        _reg(
            "bypass_hysteresis_c",
            6103,
            "holding",
            "Bypass temperature hysteresis",
            codec="scaled_s16",
            scale=0.1,
            minimum=0.0,
            maximum=5.0,
            step=0.5,
            unit="K",
            writable=True,
            restorable=True,
        ),
        _reg(
            "bypass_boost",
            6104,
            "holding",
            "Enable bypass boost",
            codec="bool",
            writable=True,
            restorable=True,
        ),
        _reg(
            "bypass_boost_level",
            6105,
            "holding",
            "Fan level used for bypass boost",
            codec="enum",
            enum=REMOTE_LEVEL,
            writable=True,
            restorable=True,
        ),
        _reg(
            "frost_control_temperature_c",
            6110,
            "holding",
            "Frost-control temperature",
            codec="scaled_s16",
            scale=0.1,
            minimum=-1.5,
            maximum=1.5,
            step=0.5,
            unit="°C",
            writable=True,
            restorable=True,
        ),
        _reg(
            "frost_min_supply_temperature_c",
            6111,
            "holding",
            "Minimum inlet temperature during frost control",
            codec="scaled_s16",
            scale=0.1,
            minimum=7.0,
            maximum=17.0,
            step=0.5,
            unit="°C",
            writable=True,
            restorable=True,
        ),
        _reg(
            "filter_warning_days",
            6120,
            "holding",
            "Days before filter warning",
            minimum=1,
            maximum=365,
            step=1,
            unit="days",
            writable=True,
            restorable=True,
        ),
        _reg(
            "external_heater_mode",
            6130,
            "holding",
            "External heater type",
            codec="enum",
            enum={0: "unavailable", 1: "preheater", 2: "postheater"},
            writable=True,
            restorable=True,
        ),
        _reg(
            "postheater_setpoint_c",
            6131,
            "holding",
            "Postheater setpoint",
            codec="scaled_s16",
            scale=0.1,
            minimum=15.0,
            maximum=30.0,
            step=0.5,
            unit="°C",
            writable=True,
            restorable=True,
        ),
        _reg(
            "humidity_control",
            6140,
            "holding",
            "Humidity control",
            codec="bool",
            writable=True,
            restorable=True,
        ),
        _reg(
            "humidity_sensitivity",
            6141,
            "holding",
            "Humidity-control sensitivity",
            codec="s16",
            minimum=-2,
            maximum=2,
            step=1,
            writable=True,
            restorable=True,
        ),
        _reg(
            "co2_control",
            6150,
            "holding",
            "CO₂ control",
            codec="bool",
            writable=True,
            restorable=True,
        ),
    ]

    for sensor in range(1, 5):
        regs.extend(
            [
                _reg(
                    f"co2_sensor_{sensor}_low_ppm",
                    6151 + (sensor - 1) * 2,
                    "holding",
                    f"CO₂ sensor {sensor} low threshold",
                    minimum=400,
                    maximum=2000,
                    step=1,
                    unit="ppm",
                    writable=True,
                    restorable=True,
                ),
                _reg(
                    f"co2_sensor_{sensor}_high_ppm",
                    6152 + (sensor - 1) * 2,
                    "holding",
                    f"CO₂ sensor {sensor} high threshold",
                    minimum=400,
                    maximum=2000,
                    step=1,
                    unit="ppm",
                    writable=True,
                    restorable=True,
                ),
            ]
        )

    digital_mode = {
        0: "off",
        1: "on",
        2: "on_if_bypass_conditions",
        3: "bypass_control",
        4: "external_valve_control",
    }
    regs.extend(
        [
            _reg(
                "signal_output_mode",
                6170,
                "holding",
                "24 V signal output function",
                codec="enum",
                enum={
                    0: "off",
                    1: "filter_warning",
                    2: "error",
                    3: "filter_warning_and_error",
                },
                writable=True,
                restorable=True,
            ),
            _reg(
                "central_heating_exhaust_connected",
                6171,
                "holding",
                "Central-heating exhaust connected",
                codec="bool",
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_1_contact_type",
                6200,
                "holding",
                "Digital input 1 contact type",
                codec="enum",
                enum={0: "normally_open", 1: "normally_closed"},
                enum_aliases={"no": "normally_open", "nc": "normally_closed"},
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_1_mode",
                6201,
                "holding",
                "Digital input 1 function",
                codec="enum",
                enum=digital_mode,
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_1_supply_fan_function",
                6202,
                "holding",
                "Supply fan behavior for digital input 1",
                codec="enum",
                enum=FAN_INPUT_FUNCTION,
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_1_exhaust_fan_function",
                6203,
                "holding",
                "Exhaust fan behavior for digital input 1",
                codec="enum",
                enum=FAN_INPUT_FUNCTION,
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_2_contact_type",
                6210,
                "holding",
                "Digital input 2 contact type",
                codec="enum",
                enum={0: "normally_open", 1: "normally_closed"},
                enum_aliases={"no": "normally_open", "nc": "normally_closed"},
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_2_mode",
                6211,
                "holding",
                "Digital input 2 function",
                codec="enum",
                enum=digital_mode,
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_2_supply_fan_function",
                6212,
                "holding",
                "Supply fan behavior for digital input 2",
                codec="enum",
                enum=FAN_INPUT_FUNCTION,
                writable=True,
                restorable=True,
            ),
            _reg(
                "digital_input_2_exhaust_fan_function",
                6213,
                "holding",
                "Exhaust fan behavior for digital input 2",
                codec="enum",
                enum=FAN_INPUT_FUNCTION,
                writable=True,
                restorable=True,
            ),
            _reg(
                "analog_input_1_enabled",
                6220,
                "holding",
                "Enable analogue input 1",
                codec="bool",
                writable=True,
                restorable=True,
            ),
            _reg(
                "analog_input_1_min_v",
                6221,
                "holding",
                "Analogue input 1 minimum voltage",
                codec="scaled_u16",
                scale=0.1,
                minimum=0.0,
                maximum=10.0,
                step=0.5,
                unit="V",
                writable=True,
                restorable=True,
            ),
            _reg(
                "analog_input_1_max_v",
                6222,
                "holding",
                "Analogue input 1 maximum voltage",
                codec="scaled_u16",
                scale=0.1,
                minimum=0.0,
                maximum=10.0,
                step=0.5,
                unit="V",
                writable=True,
                restorable=True,
            ),
            _reg(
                "analog_input_2_enabled",
                6230,
                "holding",
                "Enable analogue input 2",
                codec="bool",
                writable=True,
                restorable=True,
            ),
            _reg(
                "analog_input_2_min_v",
                6231,
                "holding",
                "Analogue input 2 minimum voltage",
                codec="scaled_u16",
                scale=0.1,
                minimum=0.0,
                maximum=10.0,
                step=0.5,
                unit="V",
                writable=True,
                restorable=True,
            ),
            _reg(
                "analog_input_2_max_v",
                6232,
                "holding",
                "Analogue input 2 maximum voltage",
                codec="scaled_u16",
                scale=0.1,
                minimum=0.0,
                maximum=10.0,
                step=0.5,
                unit="V",
                writable=True,
                restorable=True,
            ),
            _reg(
                "geo_heat_exchanger_enabled",
                6240,
                "holding",
                "Enable ground heat exchanger",
                codec="bool",
                writable=True,
                restorable=True,
                optional=True,
            ),
            _reg(
                "geo_heat_exchanger_min_temperature_c",
                6241,
                "holding",
                "Ground heat exchanger minimum temperature",
                codec="scaled_s16",
                scale=0.1,
                minimum=0.0,
                maximum=10.0,
                step=0.1,
                unit="°C",
                writable=True,
                restorable=True,
                optional=True,
            ),
            _reg(
                "geo_heat_exchanger_max_temperature_c",
                6242,
                "holding",
                "Ground heat exchanger maximum temperature",
                codec="scaled_s16",
                scale=0.1,
                minimum=15.0,
                maximum=40.0,
                step=0.1,
                unit="°C",
                writable=True,
                restorable=True,
                optional=True,
            ),
            _reg(
                "geo_heat_exchanger_default_valve",
                6243,
                "holding",
                "Ground heat exchanger valve position at 0 V",
                codec="enum",
                enum={0: "closed", 1: "open"},
                writable=True,
                restorable=True,
                optional=True,
            ),
            _reg(
                "geo_heat_exchanger_output",
                6244,
                "holding",
                "Ground heat exchanger output assignment",
                codec="enum",
                enum={
                    0: "analog_output_1",
                    1: "analog_output_2",
                    2: "relay_output_1",
                    3: "relay_output_2",
                },
                writable=True,
                restorable=True,
                optional=True,
            ),
            _reg(
                "language",
                6900,
                "holding",
                "Display language",
                codec="enum",
                enum={0: "english", 1: "dutch"},
                writable=True,
                restorable=True,
            ),
            _reg(
                "date_format",
                6901,
                "holding",
                "Display date format",
                codec="enum",
                enum={0: "dd_mm_yyyy", 1: "mm_dd_yyyy"},
                writable=True,
                restorable=True,
            ),
            _reg(
                "time_notation",
                6902,
                "holding",
                "Display time notation",
                codec="enum",
                enum={0: "12_hour", 1: "24_hour"},
                writable=True,
                restorable=True,
            ),
            _reg(
                "device_date_month_day",
                6903,
                "holding",
                "Device month/day",
                codec="packed_month_day",
                writable=True,
                restorable=False,
            ),
            _reg(
                "device_date_year",
                6904,
                "holding",
                "Device year",
                minimum=2000,
                maximum=2099,
                writable=True,
                restorable=False,
            ),
            _reg(
                "device_time",
                6905,
                "holding",
                "Device hour/minute",
                codec="packed_hm",
                writable=True,
                restorable=False,
            ),
            _reg(
                "device_weekday_second",
                6906,
                "holding",
                "Device weekday/second",
                codec="packed_weekday_second",
                writable=True,
                restorable=False,
            ),
            _reg(
                "modbus_interface_type",
                7990,
                "holding",
                "Modbus interface routing",
                codec="enum",
                enum={0: "internal", 1: "external_modbus", 2: "external_customer"},
                writable=True,
                dangerous=True,
                restorable=False,
                poll="static",
            ),
            _reg(
                "modbus_slave_address",
                7991,
                "holding",
                "Appliance Modbus slave address",
                minimum=1,
                maximum=247,
                writable=True,
                dangerous=True,
                restorable=False,
                poll="static",
            ),
            _reg(
                "modbus_speed",
                7992,
                "holding",
                "Appliance serial baud rate",
                codec="enum",
                enum={
                    0: "1200",
                    1: "2400",
                    2: "4800",
                    3: "9600",
                    4: "19200",
                    5: "38400",
                    6: "56000",
                    7: "115200",
                },
                writable=True,
                dangerous=True,
                restorable=False,
                poll="static",
            ),
            _reg(
                "remote_control_mode",
                8000,
                "holding",
                "External Modbus control mode",
                codec="enum",
                enum={0: "off", 1: "level", 2: "airflow"},
                enum_aliases={"switch": "level", "flow": "airflow"},
                writable=True,
                restorable=True,
                poll="slow",
            ),
            _reg(
                "remote_ventilation_level",
                8001,
                "holding",
                "Requested external ventilation level",
                codec="enum",
                enum=REMOTE_LEVEL,
                writable=True,
                restorable=True,
                poll="slow",
            ),
            _reg(
                "remote_airflow_m3h",
                8002,
                "holding",
                "Requested external airflow",
                codec="flow_cwl325",
                minimum=50,
                maximum=325,
                step=1,
                extra_values=(0,),
                unit="m³/h",
                writable=True,
                restorable=True,
                poll="slow",
            ),
            _reg(
                "remote_standby",
                8003,
                "holding",
                "External standby state/command",
                codec="standby_command",
                writable=True,
                restorable=True,
                poll="slow",
            ),
            _reg(
                "filter_reset_status",
                8010,
                "holding",
                "Filter-reset action/status",
                codec="enum",
                enum={0: "no_action", 1: "executed", 255: "failed"},
                writable=True,
                dangerous=False,
                one_shot=True,
                restorable=False,
                poll="never",
            ),
            _reg(
                "appliance_reset_status",
                8011,
                "holding",
                "Appliance-reset action/status",
                codec="enum",
                enum={0: "no_action", 1: "executed", 255: "failed"},
                writable=True,
                dangerous=True,
                one_shot=True,
                restorable=False,
                poll="never",
            ),
        ]
    )
    return regs


REGISTER_LIST: Final[list[RegisterDef]] = _input_registers() + _holding_registers()
REGISTERS: Final[dict[str, RegisterDef]] = {
    register.key: register for register in REGISTER_LIST
}
if len(REGISTERS) != len(REGISTER_LIST):
    raise RuntimeError("duplicate register key")

REGISTER_ALIASES: Final[dict[str, str]] = {
    "fan_mode": "remote_control_mode",
    "control_mode": "remote_control_mode",
    "fan_level": "remote_ventilation_level",
    "level": "remote_ventilation_level",
    "airflow": "remote_airflow_m3h",
    "airflow_m3h": "remote_airflow_m3h",
    "standby": "remote_standby",
    "bypass": "bypass_mode",
}


@dataclass(frozen=True, slots=True)
class ReadBlock:
    table: TableName
    tier: PollTier
    start: int
    count: int
    optional: bool = False
    extension_only: bool = False


READ_BLOCKS: Final[tuple[ReadBlock, ...]] = (
    # Live values
    ReadBlock("input", "fast", 4020, 5),
    ReadBlock("input", "fast", 4030, 8),
    ReadBlock("input", "fast", 4040, 8),
    ReadBlock("input", "fast", 4050, 2),
    ReadBlock("input", "fast", 4060, 2),
    ReadBlock("input", "fast", 4070, 3),
    ReadBlock("input", "fast", 4080, 4),
    ReadBlock("input", "fast", 4090, 1),
    ReadBlock("input", "fast", 4100, 2),
    ReadBlock("input", "fast", 4150, 1, optional=True, extension_only=True),
    ReadBlock("input", "fast", 4200, 8, optional=True),
    # Counters and optional I/O
    ReadBlock("input", "slow", 4110, 10),
    ReadBlock("input", "slow", 4420, 2, optional=True),
    ReadBlock("input", "slow", 4520, 5, optional=True, extension_only=True),
    ReadBlock("input", "slow", 4541, 4, optional=True, extension_only=True),
    # Identity/version data
    ReadBlock("input", "static", 4000, 6),
    ReadBlock("input", "static", 4010, 3),
    ReadBlock("input", "static", 4400, 6, optional=True),
    ReadBlock("input", "static", 4410, 6, optional=True),
    ReadBlock("input", "static", 4500, 6, optional=True, extension_only=True),
    # Settings
    ReadBlock("holding", "slow", 6000, 4),
    ReadBlock("holding", "slow", 6010, 8),
    ReadBlock("holding", "slow", 6030, 7),
    ReadBlock("holding", "slow", 6100, 6),
    ReadBlock("holding", "slow", 6110, 2),
    ReadBlock("holding", "slow", 6120, 1),
    ReadBlock("holding", "slow", 6130, 2),
    ReadBlock("holding", "slow", 6140, 2),
    ReadBlock("holding", "slow", 6150, 9, optional=True),
    ReadBlock("holding", "slow", 6170, 2),
    ReadBlock("holding", "slow", 6200, 4, optional=True, extension_only=True),
    ReadBlock("holding", "slow", 6210, 4, optional=True, extension_only=True),
    ReadBlock("holding", "slow", 6220, 3, optional=True, extension_only=True),
    ReadBlock("holding", "slow", 6230, 3, optional=True, extension_only=True),
    ReadBlock("holding", "slow", 6240, 5, optional=True, extension_only=True),
    ReadBlock("holding", "slow", 6900, 7),
    ReadBlock("holding", "slow", 8000, 4),
    ReadBlock("holding", "static", 7990, 3),
)


def resolve_register_name(name: str) -> str:
    key = _slug(name)
    key = REGISTER_ALIASES.get(key, key)
    if key not in REGISTERS:
        close = sorted(k for k in REGISTERS if key in k or k in key)
        hint = f"; possible matches: {', '.join(close[:8])}" if close else ""
        raise RegisterError(f"unknown register/setting {name!r}{hint}")
    return key


# ---------------------------------------------------------------------------
# Configuration and profiles
# ---------------------------------------------------------------------------


DEFAULT_CONFIG: Final[dict[str, Any]] = {
    "schema_version": 1,
    "connection": {
        "host": "192.168.1.200",
        "port": 502,
        "device_id": 20,
        "address_offset": 0,
        "transport": "modbus_tcp",
        "timeout_seconds": 3.0,
        "client_retries": 2,
        "request_retries": 2,
        "reconnect_delay_seconds": 1.0,
        "reconnect_delay_max_seconds": 30.0,
    },
    "polling": {
        "fast_interval_seconds": 5.0,
        "slow_interval_seconds": 60.0,
        "static_interval_seconds": 300.0,
        "reconcile_interval_seconds": 30.0,
        "read_holding_registers": True,
        "read_extension_registers": True,
    },
    "persistence": {
        "restore_on_startup": True,
        "restore_on_reconnect": True,
        "enforce_desired_state": True,
        "verify_writes": True,
        "verify_attempts": 5,
        "verify_delay_seconds": 0.25,
    },
    "profiles_dir": "profiles",
    "state_file": "wolf_state.json",
    "desired": {},
    "last_profile": None,
}


def _deep_merge(
    defaults: Mapping[str, Any], supplied: Mapping[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(dict(defaults))
    for key, value in supplied.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _atomic_json_write_sync(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        with contextlib.suppress(OSError):
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)
        raise


async def atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    await asyncio.to_thread(_atomic_json_write_sync, path, payload)


async def read_json(path: Path) -> dict[str, Any]:
    def _read() -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except FileNotFoundError as exc:
            raise ConfigError(f"configuration file does not exist: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ConfigError(f"top-level JSON value in {path} must be an object")
        return loaded

    return await asyncio.to_thread(_read)


def _validate_cross_settings(settings: Mapping[str, JSONScalar]) -> None:
    def numeric(key: str) -> float:
        value = settings[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(f"{key}: expected a normalized numeric value")
        return float(value)

    def ordered(keys: Sequence[str], label: str) -> None:
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
                    f"{label}: {left_key} ({left}) must not exceed {right_key} ({right})"
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
    ordered(
        [
            "pwm_supply_holiday_pct",
            "pwm_supply_low_pct",
            "pwm_supply_normal_pct",
            "pwm_supply_high_pct",
        ],
        "supply PWM presets",
    )
    ordered(
        [
            "pwm_exhaust_holiday_pct",
            "pwm_exhaust_low_pct",
            "pwm_exhaust_normal_pct",
            "pwm_exhaust_high_pct",
        ],
        "exhaust PWM presets",
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
                f"{key} is a dangerous communication/reset setting; explicit opt-in is required"
            )
        if require_restorable and not register.restorable:
            raise RegisterError(f"{key} must not be restored automatically")
        normalized[key] = register.normalize(value)
    _validate_cross_settings(normalized)
    return normalized


class ConfigStore:
    """Concurrency-safe, atomically persisted JSON configuration."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    @property
    def data(self) -> dict[str, Any]:
        if self._data is None:
            raise ConfigError("configuration has not been loaded")
        return copy.deepcopy(self._data)

    async def load(self) -> dict[str, Any]:
        async with self._lock:
            supplied = await read_json(self.path)
            merged = _deep_merge(DEFAULT_CONFIG, supplied)
            self._validate(merged)
            canonical_desired = normalize_settings(
                merged.get("desired", {}), require_restorable=True
            )
            merged["desired"] = canonical_desired
            self._data = merged
            return copy.deepcopy(merged)

    async def save(self) -> None:
        async with self._lock:
            if self._data is None:
                raise ConfigError("configuration has not been loaded")
            await atomic_json_write(self.path, self._data)

    async def update_desired(
        self,
        patch: Mapping[str, JSONScalar] | None = None,
        *,
        unset: Sequence[str] = (),
        replace: bool = False,
        last_profile: str | None = None,
    ) -> dict[str, JSONScalar]:
        async with self._lock:
            if self._data is None:
                raise ConfigError("configuration has not been loaded")
            current: dict[str, JSONScalar] = (
                {} if replace else dict(self._data.get("desired", {}))
            )
            for name in unset:
                current.pop(resolve_register_name(name), None)
            if patch:
                current.update(patch)
            _validate_cross_settings(current)
            self._data["desired"] = current
            self._data["last_profile"] = last_profile
            await atomic_json_write(self.path, self._data)
            return copy.deepcopy(current)

    def resolve_relative_path(self, configured: str | None) -> Path | None:
        if configured is None or str(configured).strip() == "":
            return None
        path = Path(str(configured)).expanduser()
        if not path.is_absolute():
            path = self.path.parent / path
        return path.resolve()

    @staticmethod
    def _validate(config: Mapping[str, Any]) -> None:
        if config.get("schema_version") != 1:
            raise ConfigError("only schema_version 1 is supported")
        connection = config.get("connection")
        polling = config.get("polling")
        persistence = config.get("persistence")
        if (
            not isinstance(connection, Mapping)
            or not isinstance(polling, Mapping)
            or not isinstance(persistence, Mapping)
        ):
            raise ConfigError(
                "connection, polling, and persistence must be JSON objects"
            )
        host = str(connection.get("host", "")).strip()
        if not host:
            raise ConfigError("connection.host must not be empty")
        port = int(connection.get("port", 0))
        if not 1 <= port <= 65535:
            raise ConfigError("connection.port must be 1..65535")
        device_id = int(connection.get("device_id", 0))
        if not 1 <= device_id <= 247:
            raise ConfigError("connection.device_id must be 1..247")
        offset = int(connection.get("address_offset", 0))
        if offset not in (-1, 0):
            raise ConfigError("connection.address_offset must be 0 (normal) or -1")
        if connection.get("transport") not in {"modbus_tcp", "rtu_over_tcp"}:
            raise ConfigError(
                "connection.transport must be 'modbus_tcp' or 'rtu_over_tcp'"
            )
        for key in (
            "fast_interval_seconds",
            "slow_interval_seconds",
            "static_interval_seconds",
            "reconcile_interval_seconds",
        ):
            if float(polling.get(key, 0)) <= 0:
                raise ConfigError(f"polling.{key} must be greater than zero")
        if int(persistence.get("verify_attempts", 0)) < 1:
            raise ConfigError("persistence.verify_attempts must be at least 1")
        desired = config.get("desired", {})
        if not isinstance(desired, Mapping):
            raise ConfigError("desired must be a JSON object")


@dataclass(slots=True)
class ResolvedProfile:
    name: str
    description: str
    settings: dict[str, JSONScalar]
    unset: list[str]
    replace: bool
    sources: list[str]


class ProfileLoader:
    """Load recursively composable partial configuration profiles."""

    VALID_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    async def list_profiles(self) -> list[str]:
        def _list() -> list[str]:
            if not self.directory.exists():
                return []
            return sorted(
                path.stem for path in self.directory.glob("*.json") if path.is_file()
            )

        return await asyncio.to_thread(_list)

    async def load(self, name: str) -> ResolvedProfile:
        return await self._load_recursive(name, stack=[])

    async def _load_recursive(self, name: str, stack: list[str]) -> ResolvedProfile:
        if not self.VALID_NAME.fullmatch(name):
            raise ProfileError(f"invalid profile name {name!r}")
        if name in stack:
            raise ProfileError(
                f"profile inheritance cycle: {' -> '.join([*stack, name])}"
            )
        path = (self.directory / f"{name}.json").resolve()
        try:
            path.relative_to(self.directory.resolve())
        except ValueError as exc:
            raise ProfileError("profile path escapes profiles_dir") from exc
        if not path.exists():
            raise ProfileError(f"profile {name!r} does not exist in {self.directory}")
        document = await read_json(path)
        extends_raw = document.get("extends", [])
        if isinstance(extends_raw, str):
            extends = [extends_raw]
        elif isinstance(extends_raw, list) and all(
            isinstance(item, str) for item in extends_raw
        ):
            extends = list(extends_raw)
        else:
            raise ProfileError(f"{name}: extends must be a string or list of strings")
        settings_raw = document.get("settings", {})
        if not isinstance(settings_raw, Mapping):
            raise ProfileError(f"{name}: settings must be an object")
        unset_raw = document.get("unset", [])
        if not isinstance(unset_raw, list) or not all(
            isinstance(item, str) for item in unset_raw
        ):
            raise ProfileError(f"{name}: unset must be a list of setting names")

        merged_settings: dict[str, JSONScalar] = {}
        merged_unset: list[str] = []
        sources: list[str] = []
        for parent_name in extends:
            parent = await self._load_recursive(parent_name, [*stack, name])
            merged_settings.update(parent.settings)
            for key in parent.unset:
                merged_settings.pop(key, None)
                if key not in merged_unset:
                    merged_unset.append(key)
            sources.extend(parent.sources)

        child_settings = normalize_settings(settings_raw, require_restorable=True)
        for unset_name in unset_raw:
            unset_key = resolve_register_name(unset_name)
            register = REGISTERS[unset_key]
            if not register.restorable:
                raise ProfileError(
                    f"{name}: {unset_key} cannot be present in desired state"
                )
            merged_settings.pop(unset_key, None)
            if unset_key not in merged_unset:
                merged_unset.append(unset_key)
        for key, value in child_settings.items():
            merged_settings[key] = value
            with contextlib.suppress(ValueError):
                merged_unset.remove(key)
        _validate_cross_settings(merged_settings)
        sources.append(name)
        return ResolvedProfile(
            name=name,
            description=str(document.get("description", "")),
            settings=merged_settings,
            unset=merged_unset,
            replace=bool(document.get("replace", False)),
            sources=list(dict.fromkeys(sources)),
        )


# ---------------------------------------------------------------------------
# Runtime state and controller
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ValueState:
    key: str
    value: JSONValue | None = None
    raw: JSONValue | None = None
    unit: str | None = None
    available: bool = False
    updated_at: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "raw": self.raw,
            "unit": self.unit,
            "available": self.available,
            "updated_at": self.updated_at,
            "error": self.error,
        }


UpdateCallback: TypeAlias = Callable[[dict[str, Any]], Awaitable[None] | None]


class WolfCWL2:
    """Async WOLF CWL-2-325 controller and state cache."""

    def __init__(self, config_path: str | Path = "wolf_cwl2_config.json") -> None:
        self.config_store = ConfigStore(config_path)
        self.config: dict[str, Any] | None = None
        self.profile_loader: ProfileLoader | None = None
        self._client: AsyncModbusTcpClient | None = None
        self._io_lock = asyncio.Lock()
        self._state_write_lock = asyncio.Lock()
        self._values: dict[str, ValueState] = {
            key: ValueState(key=key, unit=register.unit)
            for key, register in REGISTERS.items()
        }
        self._running = False
        self._read_only = False
        self._tasks: list[asyncio.Task[Any]] = []
        self._stop_event = asyncio.Event()
        self._callbacks: set[UpdateCallback] = set()
        self._subscriber_queues: set[asyncio.Queue[dict[str, Any]]] = set()
        self._connection_generation = 0
        self._last_restored_generation = -1
        self._last_connection_error: str | None = None
        self._last_poll_at: dict[str, str | None] = {
            "fast": None,
            "slow": None,
            "static": None,
        }

    async def load_config(self) -> dict[str, Any]:
        self.config = await self.config_store.load()
        profiles_path = self.config_store.resolve_relative_path(
            self.config.get("profiles_dir")
        )
        assert profiles_path is not None
        self.profile_loader = ProfileLoader(profiles_path)
        return copy.deepcopy(self.config)

    async def start(
        self,
        *,
        restore: bool | None = None,
        background: bool = True,
        read_only: bool = False,
    ) -> None:
        """Load config, poll once, restore desired settings, and start loops."""
        if self._running:
            return
        if self.config is None:
            await self.load_config()
        assert self.config is not None
        self._read_only = read_only
        self._stop_event.clear()
        self._running = True

        # Initial reads are deliberately tolerant of an offline gateway.  The
        # background loops will keep trying.
        try:
            await self.poll_once()
        except CommunicationError as exc:
            LOGGER.warning("initial Modbus poll failed: %s", exc)

        should_restore = bool(self.config["persistence"]["restore_on_startup"])
        if restore is not None:
            should_restore = restore
        if should_restore and not self._read_only:
            result = await self.apply_desired(force=True, raise_on_error=False)
            if not result["errors"]:
                self._last_restored_generation = self._connection_generation

        await self._write_state_file()
        if background:
            polling = self.config["polling"]
            self._tasks = [
                asyncio.create_task(
                    self._poll_loop("fast", float(polling["fast_interval_seconds"])),
                    name="wolf-cwl2-fast-poll",
                ),
                asyncio.create_task(
                    self._poll_loop("slow", float(polling["slow_interval_seconds"])),
                    name="wolf-cwl2-slow-poll",
                ),
                asyncio.create_task(
                    self._poll_loop(
                        "static", float(polling["static_interval_seconds"])
                    ),
                    name="wolf-cwl2-static-poll",
                ),
            ]
            if not self._read_only:
                self._tasks.append(
                    asyncio.create_task(
                        self._reconcile_loop(), name="wolf-cwl2-reconcile"
                    )
                )

    async def stop(self) -> None:
        if not self._running and self._client is None:
            return
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        async with self._io_lock:
            self._close_client_locked()
        self._running = False
        await self._write_state_file()

    async def __aenter__(self) -> "WolfCWL2":
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.stop()

    @property
    def connected(self) -> bool:
        return bool(self._client is not None and self._client.connected)

    @property
    def desired(self) -> dict[str, JSONScalar]:
        if self.config is None:
            return {}
        return copy.deepcopy(self.config.get("desired", {}))

    def get_value(self, name: str, default: Any = None) -> Any:
        key = resolve_register_name(name)
        state = self._values[key]
        return state.value if state.available else default

    def get_state(self, name: str) -> dict[str, Any]:
        key = resolve_register_name(name)
        return copy.deepcopy(self._values[key].as_dict())

    def snapshot(self, *, available_only: bool = False) -> dict[str, Any]:
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

    def subscribe(self, callback: UpdateCallback) -> Callable[[], None]:
        self._callbacks.add(callback)

        def unsubscribe() -> None:
            self._callbacks.discard(callback)

        return unsubscribe

    async def updates(
        self, *, queue_size: int = 200
    ) -> AsyncIterator[dict[str, JSONValue]]:
        queue: asyncio.Queue[dict[str, JSONValue]] = asyncio.Queue(maxsize=queue_size)
        self._subscriber_queues.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscriber_queues.discard(queue)

    async def poll_once(
        self, tiers: Sequence[PollTier] = ("fast", "slow", "static")
    ) -> None:
        for tier in tiers:
            if tier == "never":
                continue
            await self._poll_tier(tier)

    async def refresh(self, name: str) -> JSONValue | None:
        key = resolve_register_name(name)
        register = REGISTERS[key]
        await self._read_definition(register)
        return self._values[key].value

    async def set_setting(
        self,
        name: str,
        value: Any,
        *,
        persist: bool = True,
        verify: bool | None = None,
        allow_dangerous: bool = False,
    ) -> JSONValue | None:
        result = await self.set_settings(
            {name: value},
            persist=persist,
            verify=verify,
            allow_dangerous=allow_dangerous,
        )
        key = resolve_register_name(name)
        return result[key]

    async def set_settings(
        self,
        changes: Mapping[str, Any],
        *,
        persist: bool = True,
        verify: bool | None = None,
        allow_dangerous: bool = False,
        last_profile: str | None = None,
        replace_desired: bool = False,
        unset: Sequence[str] = (),
        raise_on_error: bool = True,
    ) -> dict[str, JSONValue | None]:
        if self._read_only:
            raise RegisterError("controller is in read-only mode")
        if self.config is None:
            await self.load_config()
        assert self.config is not None
        normalized = normalize_settings(changes, allow_dangerous=allow_dangerous)
        current_desired = {} if replace_desired else self.desired
        for item in unset:
            current_desired.pop(resolve_register_name(item), None)
        if persist:
            for key in normalized:
                if not REGISTERS[key].restorable:
                    raise RegisterError(f"{key} must not be persisted/restored")
            candidate = {**current_desired, **normalized}
            _validate_cross_settings(candidate)
            updated = await self.config_store.update_desired(
                normalized,
                unset=unset,
                replace=replace_desired,
                last_profile=last_profile,
            )
            self.config["desired"] = updated
            self.config["last_profile"] = last_profile
        else:
            candidate = {**current_desired, **normalized}
            _validate_cross_settings(candidate)

        results: dict[str, JSONValue | None] = {}
        errors: dict[str, str] = {}
        for key in self._write_order(normalized):
            try:
                results[key] = await self._write_definition(
                    REGISTERS[key],
                    normalized[key],
                    verify=verify,
                    allow_dangerous=allow_dangerous,
                )
            except (WolfError, OSError) as exc:
                errors[key] = str(exc)
                # A network failure means subsequent writes will almost certainly
                # fail too; retain them in desired state for the next reconcile.
                if isinstance(exc, CommunicationError):
                    for remaining in self._write_order(normalized):
                        if remaining not in results and remaining not in errors:
                            errors[remaining] = (
                                "not attempted after communication failure"
                            )
                    break
        await self._write_state_file()
        if errors and raise_on_error:
            raise BulkWriteError(
                "one or more settings could not be applied; desired state remains saved for retry",
                results,
                errors,
            )
        return results

    async def set_ventilation_level(
        self, level: str | int, *, persist: bool = True
    ) -> dict[str, JSONValue | None]:
        return await self.set_settings(
            {"remote_ventilation_level": level, "remote_control_mode": "level"},
            persist=persist,
        )

    async def set_airflow(
        self, airflow_m3h: int, *, persist: bool = True
    ) -> dict[str, JSONValue | None]:
        return await self.set_settings(
            {"remote_airflow_m3h": airflow_m3h, "remote_control_mode": "airflow"},
            persist=persist,
        )

    async def disable_remote_control(self, *, persist: bool = True) -> JSONValue | None:
        return await self.set_setting("remote_control_mode", "off", persist=persist)

    async def set_standby(
        self, enabled: bool, *, persist: bool = True
    ) -> JSONValue | None:
        return await self.set_setting("remote_standby", enabled, persist=persist)

    async def set_bypass_mode(
        self, mode: str | int, *, persist: bool = True
    ) -> JSONValue | None:
        return await self.set_setting("bypass_mode", mode, persist=persist)

    async def set_flow_presets(
        self,
        *,
        holiday: int,
        low: int,
        normal: int,
        high: int,
        persist: bool = True,
    ) -> dict[str, JSONValue | None]:
        return await self.set_settings(
            {
                "flow_preset_holiday_m3h": holiday,
                "flow_preset_low_m3h": low,
                "flow_preset_normal_m3h": normal,
                "flow_preset_high_m3h": high,
            },
            persist=persist,
        )

    async def reset_filter_warning(self) -> str:
        if self._read_only:
            raise RegisterError("controller is in read-only mode")
        register = REGISTERS["filter_reset_status"]
        await self._write_raw(register, 1, allow_dangerous=False)
        await asyncio.sleep(0.2)
        try:
            await self._read_definition(register)
            value = self._values[register.key].value
        except CommunicationError:
            return "command_sent"
        return str(value)

    async def reset_appliance(self, *, confirm: bool = False) -> str:
        if not confirm:
            raise RegisterError("appliance reset requires confirm=True")
        if self._read_only:
            raise RegisterError("controller is in read-only mode")
        register = REGISTERS["appliance_reset_status"]
        await self._write_raw(register, 1, allow_dangerous=True)
        async with self._io_lock:
            self._close_client_locked()
        return "command_sent; the appliance may disconnect while rebooting"

    async def list_profiles(self) -> list[str]:
        if self.config is None:
            await self.load_config()
        assert self.profile_loader is not None
        return await self.profile_loader.list_profiles()

    async def preview_profile(self, name: str) -> ResolvedProfile:
        if self.config is None:
            await self.load_config()
        assert self.profile_loader is not None
        return await self.profile_loader.load(name)

    async def apply_profile(
        self,
        name: str,
        *,
        persist: bool = True,
        replace: bool | None = None,
        raise_on_error: bool = True,
    ) -> dict[str, JSONValue | None]:
        profile = await self.preview_profile(name)
        replace_desired = profile.replace if replace is None else replace
        return await self.set_settings(
            profile.settings,
            persist=persist,
            last_profile=profile.name if persist else None,
            replace_desired=replace_desired,
            unset=profile.unset,
            raise_on_error=raise_on_error,
        )

    async def apply_desired(
        self,
        *,
        force: bool = False,
        raise_on_error: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Apply desired config; when force=True every desired register is rewritten."""
        if self._read_only:
            return {"written": {}, "skipped": {}, "errors": {}}
        if self.config is None:
            await self.load_config()
        desired = self.desired
        written: dict[str, Any] = {}
        skipped: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key in self._write_order(desired):
            register = REGISTERS[key]
            try:
                if not force:
                    state = self._values[key]
                    if not state.available:
                        await self._read_definition(register)
                    state = self._values[key]
                    if state.available and self._values_equal(
                        register, state.value, desired[key]
                    ):
                        skipped[key] = state.value
                        continue
                written[key] = await self._write_definition(
                    register, desired[key], verify=None, allow_dangerous=False
                )
            except (WolfError, OSError) as exc:
                errors[key] = str(exc)
                if isinstance(exc, CommunicationError):
                    break
        if not errors:
            self._last_restored_generation = self._connection_generation
        await self._write_state_file()
        result = {"written": written, "skipped": skipped, "errors": errors}
        if errors and raise_on_error:
            raise BulkWriteError(
                "could not fully apply desired configuration", written, errors
            )
        return result

    async def _poll_loop(self, tier: PollTier, interval: float) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                    break
                except TimeoutError:
                    pass
                try:
                    await self._poll_tier(tier)
                except CommunicationError as exc:
                    LOGGER.warning("%s poll failed: %s", tier, exc)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("unexpected failure in %s poll loop", tier)

    async def _reconcile_loop(self) -> None:
        assert self.config is not None
        interval = float(self.config["polling"]["reconcile_interval_seconds"])
        persistence = self.config["persistence"]
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                    break
                except TimeoutError:
                    pass
                force = bool(persistence["restore_on_reconnect"]) and (
                    self._connection_generation != self._last_restored_generation
                )
                enforce = bool(persistence["enforce_desired_state"])
                if force or enforce:
                    result = await self.apply_desired(force=force, raise_on_error=False)
                    if result["errors"]:
                        LOGGER.warning(
                            "desired-state reconcile incomplete: %s", result["errors"]
                        )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("unexpected failure in reconcile loop")

    async def _poll_tier(self, tier: PollTier) -> None:
        if self.config is None:
            await self.load_config()
        assert self.config is not None
        changed = False
        for block in (item for item in READ_BLOCKS if item.tier == tier):
            if (
                block.table == "holding"
                and not self.config["polling"]["read_holding_registers"]
            ):
                continue
            if (
                block.extension_only
                and not self.config["polling"]["read_extension_registers"]
            ):
                continue
            try:
                changed = await self._read_block(block) or changed
            except RemoteModbusError as exc:
                # Optional hardware commonly returns illegal-address exceptions.
                await self._mark_block_unavailable(block, str(exc))
                if not block.optional:
                    LOGGER.warning(
                        "Modbus rejected required block %s %d..%d: %s",
                        block.table,
                        block.start,
                        block.start + block.count - 1,
                        exc,
                    )
            except CommunicationError:
                await self._mark_block_unavailable(block, "connection unavailable")
                raise
        self._last_poll_at[tier] = datetime.now(UTC).isoformat()
        if changed:
            await self._write_state_file()

    async def _read_block(self, block: ReadBlock) -> bool:
        response = await self._request_read(block.table, block.start, block.count)
        words = list(response.registers)
        if len(words) < block.count:
            raise CommunicationError(
                f"short response for {block.table} {block.start}: expected {block.count}, got {len(words)}"
            )
        changed = False
        block_end = block.start + block.count
        for register in REGISTER_LIST:
            if register.table != block.table or register.poll != block.tier:
                continue
            if (
                block.start <= register.address
                and register.address + register.count <= block_end
            ):
                offset = register.address - block.start
                changed = (
                    await self._update_value(
                        register, words[offset : offset + register.count]
                    )
                    or changed
                )
        return changed

    async def _read_definition(self, register: RegisterDef) -> ValueState:
        response = await self._request_read(
            register.table, register.address, register.count
        )
        words = list(response.registers)
        if len(words) < register.count:
            raise CommunicationError(f"short response reading {register.key}")
        await self._update_value(register, words[: register.count])
        return self._values[register.key]

    async def _request_read(self, table: TableName, address: int, count: int) -> Any:
        method = (
            "read_input_registers" if table == "input" else "read_holding_registers"
        )
        return await self._request(method, address, count=count)

    async def _request(self, method: str, address: int, **kwargs: Any) -> Any:
        if self.config is None:
            await self.load_config()
        assert self.config is not None
        connection = self.config["connection"]
        attempts = int(connection["request_retries"]) + 1
        wire_address = address + int(connection["address_offset"])
        if wire_address < 0:
            raise ConfigError(f"address offset makes register {address} negative")

        async with self._io_lock:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    await self._connect_locked()
                    assert self._client is not None
                    call = getattr(self._client, method)
                    result = await call(
                        wire_address, device_id=int(connection["device_id"]), **kwargs
                    )
                    if result.isError():
                        # A protocol exception (for example Illegal Address on an
                        # optional UWA2-E block) does not mean that the TCP link is
                        # broken.  A ModbusIOException/no-response result does.
                        if isinstance(result, ExceptionResponse):
                            raise RemoteModbusError(
                                f"{method} address {address}: {result}"
                            )
                        raise ModbusException(f"{method} address {address}: {result}")
                    self._last_connection_error = None
                    return result
                except RemoteModbusError:
                    raise
                except asyncio.CancelledError:
                    raise
                except (ModbusException, OSError, TimeoutError, ConnectionError) as exc:
                    last_error = exc
                    self._last_connection_error = f"{type(exc).__name__}: {exc}"
                    self._close_client_locked()
                    if attempt + 1 < attempts:
                        await asyncio.sleep(min(0.25 * (2**attempt), 2.0))
            raise CommunicationError(
                f"{method} register {address} failed after {attempts} attempt(s): {last_error}"
            ) from last_error

    async def _connect_locked(self) -> None:
        assert self.config is not None
        if self._client is not None and self._client.connected:
            return
        self._close_client_locked()
        connection = self.config["connection"]
        framer = (
            FramerType.SOCKET
            if connection["transport"] == "modbus_tcp"
            else FramerType.RTU
        )
        self._client = AsyncModbusTcpClient(
            str(connection["host"]),
            port=int(connection["port"]),
            framer=framer,
            timeout=float(connection["timeout_seconds"]),
            retries=int(connection["client_retries"]),
            reconnect_delay=float(connection["reconnect_delay_seconds"]),
            reconnect_delay_max=float(connection["reconnect_delay_max_seconds"]),
            name="wolf-cwl2-325",
        )
        connected = await self._client.connect()
        if not connected:
            self._close_client_locked()
            raise CommunicationError(
                f"could not connect to gateway {connection['host']}:{connection['port']}"
            )
        self._connection_generation += 1
        LOGGER.info(
            "connected to %s:%s (device id %s, generation %s)",
            connection["host"],
            connection["port"],
            connection["device_id"],
            self._connection_generation,
        )

    def _close_client_locked(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
        self._client = None

    async def _update_value(self, register: RegisterDef, words: Sequence[int]) -> bool:
        now = datetime.now(UTC).isoformat()
        try:
            value = register.decode(words)
            error = None
            available = True
        except Exception as exc:
            value = None
            error = f"decode error: {exc}"
            available = False
        raw = register.raw_json(words)
        state = self._values[register.key]
        changed = (
            state.value != value
            or state.raw != raw
            or state.available != available
            or state.error != error
        )
        state.value = value
        state.raw = raw
        state.available = available
        state.error = error
        state.updated_at = now
        if changed:
            await self._emit_update(state)
        return changed

    async def _mark_block_unavailable(self, block: ReadBlock, error: str) -> None:
        now = datetime.now(UTC).isoformat()
        end = block.start + block.count
        for register in REGISTER_LIST:
            if register.table == block.table and block.start <= register.address < end:
                state = self._values[register.key]
                changed = state.available or state.error != error
                state.available = False
                state.error = error
                state.updated_at = now
                if changed:
                    await self._emit_update(state)

    async def _emit_update(self, state: ValueState) -> None:
        update: dict[str, Any] = {"key": state.key, **state.as_dict()}
        for queue in tuple(self._subscriber_queues):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(copy.deepcopy(update))
        for callback in tuple(self._callbacks):
            try:
                returned = callback(copy.deepcopy(update))
                if inspect.isawaitable(returned):
                    future = asyncio.ensure_future(returned)
                    future.add_done_callback(self._callback_done)
            except Exception:
                LOGGER.exception("state update callback failed")

    @staticmethod
    def _callback_done(task: asyncio.Future[Any]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            LOGGER.exception("async state update callback failed")

    async def _write_definition(
        self,
        register: RegisterDef,
        value: Any,
        *,
        verify: bool | None,
        allow_dangerous: bool,
    ) -> JSONValue | None:
        if not register.writable:
            raise RegisterError(f"{register.key} is read-only")
        if register.one_shot:
            raise RegisterError(f"use the dedicated one-shot method for {register.key}")
        if register.dangerous and not allow_dangerous:
            raise RegisterError(
                f"dangerous write to {register.key} requires allow_dangerous=True"
            )
        normalized = register.normalize(value)
        words = register.encode(normalized)
        if len(words) != 1:
            raise RegisterError(
                f"multi-register writes are not implemented for {register.key}"
            )
        await self._write_raw(register, words[0], allow_dangerous=allow_dangerous)

        assert self.config is not None
        should_verify = (
            bool(self.config["persistence"]["verify_writes"])
            if verify is None
            else verify
        )
        # Changing communication settings can sever the connection immediately.
        if register.dangerous:
            should_verify = False
        if not should_verify:
            state = self._values[register.key]
            state.value = normalized
            state.raw = words[0]
            state.available = True
            state.updated_at = datetime.now(UTC).isoformat()
            state.error = None
            await self._emit_update(state)
            return normalized

        attempts = int(self.config["persistence"]["verify_attempts"])
        delay = float(self.config["persistence"]["verify_delay_seconds"])
        actual: JSONValue | None = None
        for attempt in range(attempts):
            await asyncio.sleep(delay if attempt == 0 else min(delay * 2, 1.0))
            state = await self._read_definition(register)
            actual = state.value
            if state.available and self._values_equal(register, actual, normalized):
                return actual
        raise VerificationError(
            f"{register.key}: wrote {normalized!r}, but read back {actual!r} after {attempts} attempt(s)"
        )

    async def _write_raw(
        self, register: RegisterDef, raw_word: int, *, allow_dangerous: bool
    ) -> None:
        if register.dangerous and not allow_dangerous:
            raise RegisterError(
                f"dangerous write to {register.key} requires explicit confirmation"
            )
        await self._request(
            "write_register", register.address, value=int(raw_word) & 0xFFFF
        )

    @staticmethod
    def _values_equal(register: RegisterDef, actual: Any, desired: Any) -> bool:
        if isinstance(actual, str) and actual.startswith("unknown_"):
            return False
        if (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and isinstance(desired, (int, float))
            and not isinstance(desired, bool)
        ):
            tolerance = max(register.scale / 2.0, 1e-6)
            return math.isclose(float(actual), float(desired), abs_tol=tolerance)
        return actual == desired

    @staticmethod
    def _write_order(settings: Mapping[str, Any]) -> list[str]:
        # Values first; mode last.  This avoids temporarily selecting a mode
        # before its corresponding target register has been updated.
        priority = {
            "remote_ventilation_level": 80,
            "remote_airflow_m3h": 80,
            "remote_standby": 90,
            "remote_control_mode": 100,
        }
        return sorted(
            settings,
            key=lambda key: (priority.get(key, 10), REGISTERS[key].address, key),
        )

    async def _write_state_file(self) -> None:
        if self.config is None:
            return
        state_path = self.config_store.resolve_relative_path(
            self.config.get("state_file")
        )
        if state_path is None:
            return
        async with self._state_write_lock:
            await atomic_json_write(state_path, self.snapshot())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_cli_value(text: str) -> Any:
    stripped = text.strip()
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(stripped)
    return stripped


def _profile_as_json(profile: ResolvedProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "description": profile.description,
        "extends_resolved": profile.sources,
        "replace": profile.replace,
        "unset": profile.unset,
        "settings": profile.settings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Async WOLF CWL-2-325 Modbus controller"
    )
    parser.add_argument(
        "--config", default="wolf_cwl2_config.json", help="JSON configuration path"
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR")
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init-config", help="create a new configuration and example profiles"
    )
    init.add_argument("--host", default="192.168.1.200", help="gateway IP address")
    init.add_argument(
        "--force", action="store_true", help="overwrite an existing config"
    )

    run = sub.add_parser("run", help="run continuously")
    run.add_argument(
        "--read-only",
        action="store_true",
        help="disable startup restore and all writes",
    )
    run.add_argument(
        "--print-updates",
        action="store_true",
        help="print changed values as JSON lines",
    )

    snapshot = sub.add_parser(
        "snapshot", help="read all documented values once and print JSON"
    )
    snapshot.add_argument("--available-only", action="store_true")

    get = sub.add_parser("get", help="read one named value")
    get.add_argument("name")

    set_cmd = sub.add_parser("set", help="set any named writable parameter")
    set_cmd.add_argument("name")
    set_cmd.add_argument("value", help="JSON scalar or enum text")
    set_cmd.add_argument(
        "--temporary", action="store_true", help="do not update desired config"
    )

    level = sub.add_parser("level", help="select holiday/low/normal/high")
    level.add_argument("value", choices=tuple(REMOTE_LEVEL.values()))
    level.add_argument("--temporary", action="store_true")

    airflow = sub.add_parser(
        "airflow", help="set direct airflow in m³/h (0 or 50..325)"
    )
    airflow.add_argument("value", type=int)
    airflow.add_argument("--temporary", action="store_true")

    standby = sub.add_parser("standby", help="enter or leave standby")
    standby.add_argument("value", choices=("on", "off"))
    standby.add_argument("--temporary", action="store_true")

    bypass = sub.add_parser("bypass", help="set automatic/closed/open bypass")
    bypass.add_argument("value", choices=("automatic", "closed", "open"))
    bypass.add_argument("--temporary", action="store_true")

    sub.add_parser("profiles", help="list profile files")
    preview = sub.add_parser(
        "preview-profile", help="resolve a profile without applying it"
    )
    preview.add_argument("name")
    profile = sub.add_parser("profile", help="apply a profile")
    profile.add_argument("name")
    profile.add_argument("--temporary", action="store_true")
    profile.add_argument(
        "--replace", action="store_true", help="replace entire desired configuration"
    )

    sub.add_parser("desired", help="print persistent desired settings")
    registers = sub.add_parser(
        "registers", help="print the built-in register catalogue"
    )
    registers.add_argument("--writable-only", action="store_true")

    sub.add_parser("reset-filter", help="send one-shot filter warning reset")
    reset_app = sub.add_parser("reset-appliance", help="send one-shot appliance reset")
    reset_app.add_argument("--yes", action="store_true", help="required confirmation")
    return parser


async def _init_config(config_path: Path, host: str, force: bool) -> None:
    if config_path.exists() and not force:
        raise ConfigError(f"{config_path} already exists; use --force to overwrite")
    payload = copy.deepcopy(DEFAULT_CONFIG)
    payload["connection"]["host"] = host
    await atomic_json_write(config_path, payload)
    profiles = config_path.parent / str(payload["profiles_dir"])
    profiles.mkdir(parents=True, exist_ok=True)
    examples = {
        "normal.json": {
            "description": "Normal continuous ventilation",
            "settings": {
                "remote_ventilation_level": "normal",
                "remote_control_mode": "level",
                "remote_standby": False,
            },
        },
        "night.json": {
            "description": "Quiet night ventilation",
            "settings": {
                "remote_ventilation_level": "low",
                "remote_control_mode": "level",
                "remote_standby": False,
            },
        },
        "boost.json": {
            "description": "Maximum preset ventilation",
            "settings": {
                "remote_ventilation_level": "high",
                "remote_control_mode": "level",
                "remote_standby": False,
            },
        },
        "away.json": {
            "description": "Holiday/away ventilation; keeps the appliance running at its lowest preset",
            "settings": {
                "remote_ventilation_level": "holiday",
                "remote_control_mode": "level",
                "remote_standby": False,
            },
        },
        "summer-night.json": {
            "description": "Example composed profile: night flow with bypass forced open",
            "extends": ["night"],
            "settings": {"bypass_mode": "open"},
        },
    }
    for filename, document in examples.items():
        target = profiles / filename
        if not target.exists() or force:
            await atomic_json_write(target, document)
    print(f"created {config_path}")
    print(f"created example profiles in {profiles}")


async def _run_cli(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser().resolve()
    if args.command == "init-config":
        await _init_config(config_path, args.host, args.force)
        return 0

    if args.command == "registers":
        catalogue: dict[str, Any] = {}
        for key, register in sorted(
            REGISTERS.items(), key=lambda item: (item[1].table, item[1].address)
        ):
            if args.writable_only and not register.writable:
                continue
            catalogue[key] = {
                "address": register.address,
                "table": register.table,
                "description": register.description,
                "unit": register.unit,
                "writable": register.writable,
                "restorable": register.restorable,
                "dangerous": register.dangerous,
                "one_shot": register.one_shot,
                "poll": register.poll,
                "allowed": list(register.enum.values()) if register.enum else None,
                "minimum": register.minimum,
                "maximum": register.maximum,
                "step": register.step,
                "extra_values": list(register.extra_values),
            }
        print(json.dumps(catalogue, indent=2, ensure_ascii=False))
        return 0

    controller = WolfCWL2(config_path)

    if args.command in {"profiles", "preview-profile", "desired"}:
        await controller.load_config()
        if args.command == "profiles":
            print(json.dumps(await controller.list_profiles(), indent=2))
        elif args.command == "preview-profile":
            print(
                json.dumps(
                    _profile_as_json(await controller.preview_profile(args.name)),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(json.dumps(controller.desired, indent=2, ensure_ascii=False))
        return 0

    if args.command == "run":
        if args.print_updates:
            controller.subscribe(
                lambda update: print(json.dumps(update, ensure_ascii=False), flush=True)
            )
        await controller.start(read_only=args.read_only, background=True)
        loop = asyncio.get_running_loop()
        shutdown = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, shutdown.set)
        LOGGER.info("controller running; press Ctrl-C to stop")
        await shutdown.wait()
        await controller.stop()
        return 0

    # One-shot commands do not start background tasks. Snapshot is always
    # read-only and therefore cannot unexpectedly restore desired settings.
    if args.command in {"snapshot", "get"}:
        await controller.start(restore=False, background=False, read_only=True)
    else:
        await controller.start(restore=True, background=False, read_only=False)
    try:
        if args.command == "snapshot":
            print(
                json.dumps(
                    controller.snapshot(available_only=args.available_only),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif args.command == "get":
            await controller.refresh(args.name)
            print(
                json.dumps(
                    controller.get_state(args.name), indent=2, ensure_ascii=False
                )
            )
        elif args.command == "set":
            result = await controller.set_setting(
                args.name, _parse_cli_value(args.value), persist=not args.temporary
            )
            print(
                json.dumps(
                    {resolve_register_name(args.name): result},
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif args.command == "level":
            print(
                json.dumps(
                    await controller.set_ventilation_level(
                        args.value, persist=not args.temporary
                    ),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif args.command == "airflow":
            print(
                json.dumps(
                    await controller.set_airflow(
                        args.value, persist=not args.temporary
                    ),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif args.command == "standby":
            print(
                json.dumps(
                    {
                        "remote_standby": await controller.set_standby(
                            args.value == "on", persist=not args.temporary
                        )
                    },
                    indent=2,
                )
            )
        elif args.command == "bypass":
            print(
                json.dumps(
                    {
                        "bypass_mode": await controller.set_bypass_mode(
                            args.value, persist=not args.temporary
                        )
                    },
                    indent=2,
                )
            )
        elif args.command == "profile":
            print(
                json.dumps(
                    await controller.apply_profile(
                        args.name,
                        persist=not args.temporary,
                        replace=True if args.replace else None,
                    ),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif args.command == "reset-filter":
            print(await controller.reset_filter_warning())
        elif args.command == "reset-appliance":
            print(await controller.reset_appliance(confirm=args.yes))
        else:
            raise RuntimeError(f"unhandled command {args.command}")
    finally:
        await controller.stop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return asyncio.run(_run_cli(args))
    except KeyboardInterrupt:
        return 130
    except WolfError as exc:
        LOGGER.error("%s", exc)
        if isinstance(exc, BulkWriteError):
            LOGGER.error("partial results: %s", exc.results)
            LOGGER.error("errors: %s", exc.errors)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
