"""Behavior tests for the exhaustive Home Assistant entity overlay."""

from __future__ import annotations

from wolf_325 import REGISTERS
from wolf_325.derived_values import VIRTUAL_VALUES

from custom_components.wolf_cwl2.entity_catalogue import (
    ACTION_ONLY_KEYS,
    DEFAULT_ENABLED_KEYS,
    ENTITY_SPECS,
)


def test_overlay_classifies_every_value_exactly_once() -> None:
    """Require one HA disposition for every physical and virtual value key.

    Returns:
        None.
    """
    assert len(ENTITY_SPECS) == 156
    assert set(ENTITY_SPECS) == set(REGISTERS) | set(VIRTUAL_VALUES)
    assert all(key == spec.key for key, spec in ENTITY_SPECS.items())
    assert all(spec.translation_key == spec.key for spec in ENTITY_SPECS.values())


def test_overlay_derives_safe_platforms_without_wire_metadata() -> None:
    """Keep writable UI policy separate from canonical wire metadata.

    Returns:
        None.
    """
    for key, register in REGISTERS.items():
        spec = ENTITY_SPECS[key]
        assert not hasattr(spec, "address")
        assert not hasattr(spec, "codec")
        if register.dangerous:
            assert spec.platform in {"sensor", "action"}
        elif register.one_shot:
            assert spec.platform == "action"
        elif register.writable and register.restorable:
            expected = {
                "bool": "switch",
                "standby_command": "switch",
                "enum": "select",
            }.get(register.codec, "number")
            assert spec.platform == expected
        else:
            assert spec.platform == "sensor"


def test_guarded_and_date_time_dispositions_match_product_contract() -> None:
    """Keep resets action-only and appliance clock fields read-only.

    Returns:
        None.
    """
    assert ACTION_ONLY_KEYS == {"filter_reset_status", "appliance_reset_status"}
    for key in (
        "device_date_month_day",
        "device_date_year",
        "device_time",
        "device_weekday_second",
    ):
        assert ENTITY_SPECS[key].platform == "sensor"
    for key in (
        "modbus_interface_type",
        "modbus_slave_address",
        "modbus_speed",
    ):
        spec = ENTITY_SPECS[key]
        assert spec.platform == "sensor"
        assert spec.entity_category == "diagnostic"


def test_virtual_dew_points_are_default_temperature_sensors() -> None:
    """Expose derived dew points as ordinary measured temperature entities.

    Returns:
        None.
    """
    for key in ("supply_dew_point_c", "exhaust_dew_point_c"):
        spec = ENTITY_SPECS[key]
        assert spec.platform == "sensor"
        assert spec.enabled_default is True
        assert spec.device_class == "temperature"
        assert spec.state_class == "measurement"
        assert spec.native_unit == "°C"
        assert spec.suggested_precision == 1


def test_curated_defaults_are_explicit_and_recorder_safe() -> None:
    """Review the ordinary default surface and counter semantics.

    Returns:
        None.
    """
    assert DEFAULT_ENABLED_KEYS == {
        key for key, spec in ENTITY_SPECS.items() if spec.enabled_default
    }
    assert 20 <= len(DEFAULT_ENABLED_KEYS) <= 45
    assert "supply_airflow_actual_m3h" in DEFAULT_ENABLED_KEYS
    assert "remote_airflow_m3h" in DEFAULT_ENABLED_KEYS
    assert "modbus_slave_address" not in DEFAULT_ENABLED_KEYS
    for key in (
        "operating_time_hours",
        "filter_runtime_hours",
        "filter_air_volume_counter",
        "total_air_volume_counter",
    ):
        assert ENTITY_SPECS[key].state_class is None


def test_overlay_uses_only_reviewed_home_assistant_metadata_values() -> None:
    """Reject accidental platform, category, or state-class invention.

    Returns:
        None.
    """
    assert {spec.platform for spec in ENTITY_SPECS.values()} <= {
        "action",
        "number",
        "select",
        "sensor",
        "switch",
    }
    assert {spec.entity_category for spec in ENTITY_SPECS.values()} <= {
        None,
        "config",
        "diagnostic",
    }
    assert {spec.state_class for spec in ENTITY_SPECS.values()} <= {
        None,
        "measurement",
    }
