"""Behavior tests for TUI rows, filtering, details, and write editors."""

from __future__ import annotations

import pytest

from wolf_325.catalogue import REGISTERS
from wolf_325.tui_models import (
    build_editor_spec,
    build_register_rows,
    format_register_details,
    parse_editor_value,
)


def _snapshot() -> dict[str, object]:
    """Return representative cached state used by presentation tests."""
    return {
        "values": {
            "supply_airflow_actual_m3h": {
                "value": 170,
                "raw": 170,
                "unit": "m³/h",
                "available": True,
                "updated_at": "2026-07-18T17:00:00+00:00",
                "error": None,
            },
            "remote_airflow_m3h": {
                "value": None,
                "raw": None,
                "unit": "m³/h",
                "available": False,
                "updated_at": None,
                "error": "Modbus exception 3",
            },
        }
    }


def test_rows_show_values_errors_flags_and_desired_ownership() -> None:
    """Table rows summarize current state without hiding unavailable values."""
    rows = build_register_rows(
        ("supply_airflow_actual_m3h", "remote_airflow_m3h"),
        _snapshot(),
        desired={"remote_airflow_m3h": 200},
    )

    assert rows[0].value == "170"
    assert rows[0].status == "live"
    assert rows[1].value == "unavailable"
    assert rows[1].status == "error"
    assert "desired" in rows[1].flags
    assert "write" in rows[1].flags


def test_rows_filter_by_key_description_address_and_state() -> None:
    """Search accepts operator vocabulary, descriptions, addresses, and errors."""
    keys = ("supply_airflow_actual_m3h", "remote_airflow_m3h")

    assert [row.key for row in build_register_rows(keys, _snapshot(), search="actual")]
    assert [row.key for row in build_register_rows(keys, _snapshot(), search="8002")] == [
        "remote_airflow_m3h"
    ]
    assert [row.key for row in build_register_rows(keys, _snapshot(), search="exception 3")] == [
        "remote_airflow_m3h"
    ]


def test_details_include_wire_validation_and_runtime_metadata() -> None:
    """The detail panel explains how a selected value behaves and is encoded."""
    details = format_register_details(
        "remote_airflow_m3h",
        _snapshot()["values"]["remote_airflow_m3h"],  # type: ignore[index]
        desired=200,
    )

    assert "Holding register 8002" in details
    assert "Allowed: 50–325 m³/h; step 1; special 0" in details
    assert "Persistent desired value: 200" in details
    assert "Last error: Modbus exception 3" in details


def test_details_label_plain_read_only_register_capability() -> None:
    """Read-only values show an explicit capability instead of an empty label."""
    details = format_register_details(
        "supply_airflow_actual_m3h",
        _snapshot()["values"]["supply_airflow_actual_m3h"],  # type: ignore[index]
        is_desired=False,
    )

    assert "Capabilities: read-only" in details


def test_editor_specs_follow_enum_boolean_numeric_and_action_metadata() -> None:
    """Editor controls come from canonical codec and safety metadata."""
    mode = build_editor_spec(REGISTERS["remote_control_mode"], "level")
    boolean = build_editor_spec(REGISTERS["use_display_as_switch"], False)
    airflow = build_editor_spec(REGISTERS["remote_airflow_m3h"], 170)
    reset = build_editor_spec(REGISTERS["appliance_reset_status"], None)

    assert mode.kind == "select"
    assert mode.options == ("off", "level", "airflow")
    assert boolean.options == ("false", "true")
    assert airflow.kind == "number"
    assert airflow.persist_allowed is True
    assert reset.kind == "action"
    assert reset.confirmation_phrase == "RESET APPLIANCE"


@pytest.mark.parametrize(
    ("key", "text", "expected"),
    [
        ("use_display_as_switch", "true", True),
        ("remote_control_mode", "airflow", "airflow"),
        ("remote_airflow_m3h", "200", 200),
        ("bypass_hysteresis_c", "1.5", 1.5),
        ("device_time", "17:42", "17:42"),
    ],
)
def test_editor_values_are_parsed_and_normalized(
    key: str, text: str, expected: object
) -> None:
    """Editor submission uses the same canonical validation as controller writes."""
    assert parse_editor_value(REGISTERS[key], text) == expected


def test_editor_value_rejects_out_of_range_input() -> None:
    """Invalid writes fail before reaching the external device."""
    with pytest.raises(ValueError, match="remote_airflow_m3h"):
        parse_editor_value(REGISTERS["remote_airflow_m3h"], "326")
