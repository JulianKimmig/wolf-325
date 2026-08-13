"""Behavior tests for configuration persistence and composable profiles."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from wolf_325 import (
    DEFAULT_CONFIG,
    ConfigError,
    ConfigStore,
    ProfileError,
    ProfileLoader,
    RegisterError,
    ValidationError,
    atomic_json_write,
    normalize_settings,
    read_json,
)


async def test_json_persistence_is_round_trippable_and_creates_parents(
    tmp_path: Path,
) -> None:
    """Atomic JSON output is complete, newline-terminated, and readable."""
    path = tmp_path / "nested" / "config.json"
    await atomic_json_write(path, {"name": "Lüftung", "value": 2})
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert await read_json(path) == {"name": "Lüftung", "value": 2}
    assert not list(path.parent.glob("*.tmp"))


@pytest.mark.parametrize(
    ("content", "message"),
    [("[]", "top-level"), ("{", "invalid JSON")],
)
async def test_read_json_rejects_invalid_documents(
    tmp_path: Path, content: str, message: str
) -> None:
    """Configuration reads distinguish invalid JSON shapes from valid objects."""
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        await read_json(path)


async def test_read_json_reports_missing_file(tmp_path: Path) -> None:
    """A missing configuration fails instead of silently using defaults."""
    with pytest.raises(ConfigError, match="does not exist"):
        await read_json(tmp_path / "missing.json")


async def test_config_load_merges_defaults_and_canonicalizes_desired(
    tmp_path: Path,
) -> None:
    """Partial user config gains defaults while desired aliases become canonical."""
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "connection": {"host": "gateway"},
                "desired": {"fan_level": "HIGH"},
            }
        ),
        encoding="utf-8",
    )
    loaded = await ConfigStore(path).load()
    assert loaded["connection"]["port"] == 502
    assert loaded["desired"] == {"remote_ventilation_level": "high"}


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"schema_version": 2}, "schema_version"),
        ({"connection": {"host": ""}}, "host"),
        ({"connection": {"port": 0}}, "port"),
        ({"connection": {"device_id": 248}}, "device_id"),
        ({"connection": {"address_offset": 1}}, "address_offset"),
        ({"connection": {"transport": "serial"}}, "transport"),
        ({"polling": {"fast_interval_seconds": 0}}, "fast_interval"),
        ({"persistence": {"verify_attempts": 0}}, "verify_attempts"),
        ({"desired": []}, "desired"),
    ],
)
async def test_config_validation_rejects_invalid_operational_values(
    tmp_path: Path, patch: dict[str, object], message: str
) -> None:
    """Invalid transport, addressing, polling, and persistence values fail fast."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        await ConfigStore(path).load()


def test_desired_normalization_guards_unsafe_and_nonpersistent_values() -> None:
    """Desired state accepts safe restorable values and rejects unsafe categories."""
    assert normalize_settings(
        {"bypass": "auto"}, require_restorable=True
    ) == {"bypass_mode": "automatic"}
    with pytest.raises(RegisterError, match="read-only"):
        normalize_settings({"filter_status": "clean"})
    with pytest.raises(RegisterError, match="one-shot"):
        normalize_settings({"filter_reset_status": "executed"})
    with pytest.raises(RegisterError, match="dangerous"):
        normalize_settings({"modbus_slave_address": 10})


@pytest.mark.parametrize(
    "settings",
    [
        {"flow_preset_low_m3h": 150, "flow_preset_normal_m3h": 100},
        {"pwm_supply_low_pct": 80, "pwm_supply_normal_pct": 70},
        {"pwm_exhaust_low_pct": 80, "pwm_exhaust_normal_pct": 70},
        {"co2_sensor_1_low_ppm": 1000, "co2_sensor_1_high_ppm": 900},
        {"analog_input_1_min_v": 8, "analog_input_1_max_v": 2},
        {
            "geo_heat_exchanger_min_temperature_c": 10,
            "geo_heat_exchanger_max_temperature_c": 10,
        },
    ],
)
def test_cross_setting_constraints_reject_inverted_ranges(
    settings: dict[str, int]
) -> None:
    """Related presets and thresholds remain ordered as required by the device."""
    with pytest.raises(ValidationError):
        normalize_settings(settings)


async def test_config_update_supports_merge_unset_replace_and_profile_marker(
    config_path: Path,
) -> None:
    """Persistent desired-state ownership can be merged, released, or replaced."""
    store = ConfigStore(config_path)
    await store.load()
    await store.update_desired({"bypass_mode": "automatic"})
    merged = await store.update_desired(
        {"remote_control_mode": "level"}, last_profile="normal"
    )
    assert set(merged) == {"bypass_mode", "remote_control_mode"}
    assert await store.update_desired(unset=["bypass"]) == {
        "remote_control_mode": "level"
    }
    assert await store.update_desired(
        {"remote_standby": False}, replace=True
    ) == {"remote_standby": False}
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["desired"] == {"remote_standby": False}


async def test_profile_loader_composes_inheritance_unset_and_replace(
    tmp_path: Path,
) -> None:
    """Child profiles inherit canonical settings and can release owned values."""
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    documents = {
        "base.json": {"settings": {"fan_level": "low", "bypass": "open"}},
        "child.json": {
            "description": "child",
            "extends": "base",
            "unset": ["bypass"],
            "replace": True,
            "settings": {"remote_standby": False},
        },
    }
    for name, payload in documents.items():
        (profiles / name).write_text(json.dumps(payload), encoding="utf-8")
    loader = ProfileLoader(profiles)
    assert await loader.list_profiles() == ["base", "child"]
    resolved = await loader.load("child")
    assert resolved.settings == {
        "remote_ventilation_level": "low",
        "remote_standby": False,
    }
    assert resolved.unset == ["bypass_mode"]
    assert resolved.replace is True
    assert resolved.sources == ["base", "child"]


@pytest.mark.parametrize(
    ("documents", "name", "message"),
    [
        ({}, "missing", "does not exist"),
        ({"bad.json": {"extends": 2}}, "bad", "extends"),
        ({"bad.json": {"settings": []}}, "bad", "settings"),
        ({"bad.json": {"unset": "bypass"}}, "bad", "unset"),
        (
            {"a.json": {"extends": "b"}, "b.json": {"extends": "a"}},
            "a",
            "cycle",
        ),
    ],
)
async def test_profile_loader_reports_invalid_documents(
    tmp_path: Path,
    documents: dict[str, object],
    name: str,
    message: str,
) -> None:
    """Missing, malformed, and cyclic profiles produce domain-specific errors."""
    for filename, payload in documents.items():
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProfileError, match=message):
        await ProfileLoader(tmp_path).load(name)
