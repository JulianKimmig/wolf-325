"""Home Assistant semantics layered over the canonical register catalogue."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

from wolf_325 import REGISTERS, RegisterDef
from wolf_325.derived_values import VIRTUAL_VALUES, VirtualValueDef

EntityPlatform = Literal["action", "number", "select", "sensor", "switch"]
EntityCategoryName = Literal["config", "diagnostic"]

ACTION_ONLY_KEYS: Final = frozenset(
    {"filter_reset_status", "appliance_reset_status"}
)
READ_ONLY_DATE_TIME_KEYS: Final = frozenset(
    {
        "device_date_month_day",
        "device_date_year",
        "device_time",
        "device_weekday_second",
    }
)
COMMUNICATION_KEYS: Final = frozenset(
    {"modbus_interface_type", "modbus_slave_address", "modbus_speed"}
)
COUNTER_KEYS: Final = frozenset(
    {
        "operating_time_hours",
        "filter_runtime_hours",
        "filter_air_volume_counter",
        "total_air_volume_counter",
    }
)
DEFAULT_ENABLED_KEYS: Final = frozenset(
    {
        "active_function",
        "fan_control_type",
        "ventilation_mode",
        "supply_fan_status",
        "supply_airflow_setpoint_m3h",
        "supply_airflow_actual_m3h",
        "supply_fan_speed_rpm",
        "supply_temperature_c",
        "supply_relative_humidity_pct",
        "supply_dew_point_c",
        "exhaust_fan_status",
        "exhaust_airflow_setpoint_m3h",
        "exhaust_airflow_actual_m3h",
        "exhaust_fan_speed_rpm",
        "exhaust_temperature_c",
        "exhaust_relative_humidity_pct",
        "exhaust_dew_point_c",
        "bypass_status",
        "preheater_status",
        "preheater_capacity_pct",
        "frost_status",
        "filter_status",
        "filter_runtime_hours",
        "co2_sensor_1_status",
        "co2_sensor_1_ppm",
        "flow_preset_holiday_m3h",
        "flow_preset_low_m3h",
        "flow_preset_normal_m3h",
        "flow_preset_high_m3h",
        "flow_control_method",
        "use_display_as_switch",
        "filter_warning_days",
        "humidity_control",
        "co2_control",
        "remote_control_mode",
        "remote_ventilation_level",
        "remote_airflow_m3h",
        "remote_standby",
    }
)


@dataclass(frozen=True, slots=True)
class EntitySpec:
    """Describe HA-only presentation policy for one canonical register.

    Attributes:
        key: Canonical client register key and stable entity-ID suffix.
        platform: Native HA platform or guarded action-only disposition.
        translation_key: Stable key used for translated entity naming.
        name: English device-relative fallback name.
        enabled_default: Whether a new registry entity starts enabled.
        entity_category: Optional config or diagnostic grouping.
        device_class: Optional HA device-class string.
        state_class: Optional Recorder state-class string.
        native_unit: Engineering unit inherited from the canonical catalogue.
        suggested_precision: Display precision derived from catalogue scaling.
    """

    key: str
    platform: EntityPlatform
    translation_key: str
    name: str
    enabled_default: bool
    entity_category: EntityCategoryName | None = None
    device_class: str | None = None
    state_class: str | None = None
    native_unit: str | None = None
    suggested_precision: int | None = None


def _platform(register: RegisterDef) -> EntityPlatform:
    """Choose the reviewed HA disposition for one register.

    Args:
        register: Canonical register definition containing safety and codec data.

    Returns:
        Native platform name or the action-only disposition.
    """
    if register.key in ACTION_ONLY_KEYS:
        return "action"
    if register.key in READ_ONLY_DATE_TIME_KEYS or register.key in COMMUNICATION_KEYS:
        return "sensor"
    if not register.writable or not register.restorable:
        return "sensor"
    if register.codec in {"bool", "standby_command"}:
        return "switch"
    if register.codec == "enum":
        return "select"
    return "number"


def _device_class(register: RegisterDef) -> str | None:
    """Map proven engineering semantics to conservative HA device classes.

    Args:
        register: Canonical register definition with engineering unit and key.

    Returns:
        HA device-class value, or ``None`` when semantics are not proven.
    """
    if register.unit == "°C":
        return "temperature"
    if register.unit == "%" and "humidity" in register.key:
        return "humidity"
    return {
        "Pa": "pressure",
        "ppm": "carbon_dioxide",
        "V": "voltage",
        "m³/h": "volume_flow_rate",
        "m³": "volume",
        "h": "duration",
    }.get(register.unit)


def _category(register: RegisterDef, platform: EntityPlatform) -> EntityCategoryName | None:
    """Assign config and diagnostic grouping without hiding core telemetry.

    Args:
        register: Canonical register definition being classified.
        platform: Already selected Home Assistant platform.

    Returns:
        Entity category or ``None`` for primary device values.
    """
    if register.key in COMMUNICATION_KEYS or register.poll == "static":
        return "diagnostic"
    if platform in {"number", "select", "switch", "action"}:
        return "config"
    return None


def _build_spec(register: RegisterDef) -> EntitySpec:
    """Build one complete presentation record from reviewed policy.

    Args:
        register: Canonical register whose wire metadata remains client-owned.

    Returns:
        Immutable Home Assistant semantic description.
    """
    platform = _platform(register)
    numeric_sensor = (
        platform == "sensor"
        and register.codec
        in {"u16", "s16", "scaled_u16", "scaled_s16", "flow_cwl325"}
        and register.key not in COUNTER_KEYS
        and register.poll != "static"
    )
    return EntitySpec(
        key=register.key,
        platform=platform,
        translation_key=register.key,
        name=register.description,
        enabled_default=register.key in DEFAULT_ENABLED_KEYS,
        entity_category=_category(register, platform),
        device_class=_device_class(register),
        state_class="measurement" if numeric_sensor else None,
        native_unit=register.unit,
        suggested_precision=1 if register.scale not in {0, 1, 1.0} else None,
    )


def _build_virtual_spec(definition: VirtualValueDef) -> EntitySpec:
    """Build Home Assistant metadata for one calculated read-only value.

    Args:
        definition: Canonical virtual value definition.

    Returns:
        Immutable measured-temperature sensor description.
    """
    return EntitySpec(
        key=definition.key,
        platform="sensor",
        translation_key=definition.key,
        name=definition.description,
        enabled_default=definition.key in DEFAULT_ENABLED_KEYS,
        device_class="temperature",
        state_class="measurement",
        native_unit=definition.unit,
        suggested_precision=1,
    )


ENTITY_SPECS: Final = MappingProxyType(
    {
        **{key: _build_spec(register) for key, register in REGISTERS.items()},
        **{
            key: _build_virtual_spec(definition)
            for key, definition in VIRTUAL_VALUES.items()
        },
    }
)

__all__ = [
    "ACTION_ONLY_KEYS",
    "DEFAULT_ENABLED_KEYS",
    "ENTITY_SPECS",
    "EntitySpec",
]
