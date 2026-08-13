"""Edge-case tests for codecs, configuration, profiles, and lifecycle behavior."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from wolf_325 import (
    DEFAULT_CONFIG,
    ConfigError,
    ConfigStore,
    ProfileError,
    ProfileLoader,
    REGISTERS,
    RegisterDef,
    RegisterError,
    ValidationError,
    WolfCWL2,
    normalize_settings,
)
from wolf_325.codecs import enum_reverse
from wolf_325.config import atomic_json_write_sync, deep_merge
from wolf_325.register import ReadBlock

from conftest import FakeClient


def test_codec_mapping_pair_and_numeric_text_edge_paths() -> None:
    """Codecs report malformed mappings and accept finite numeric strings."""
    assert REGISTERS["bypass_indoor_threshold_c"].normalize("20.5") == 20.5
    with pytest.raises(ValidationError, match="pair mapping"):
        REGISTERS["device_time"].normalize({"hour": "bad", "minute": 2})
    with pytest.raises(ValidationError, match="two-part"):
        REGISTERS["device_time"].normalize(object())
    with pytest.raises(ValidationError, match="number"):
        REGISTERS["bypass_indoor_threshold_c"].normalize("warm")


def test_codec_signed_bounds_unknown_type_and_nonprintable_version() -> None:
    """Synthetic definitions exercise explicit signed bounds and unknown codecs."""
    signed = RegisterDef(
        "signed",
        1,
        "holding",
        "signed test",
        codec="s16",
        writable=True,
    )
    assert signed.encode(-32768) == [0x8000]
    with pytest.raises(ValidationError, match="signed 16-bit"):
        signed.encode(-32769)
    unknown = RegisterDef("unknown", 2, "input", "unknown test", codec="mystery")
    with pytest.raises(RuntimeError, match="unknown codec"):
        unknown.normalize(1)
    assert REGISTERS["base_software_version"].decode([1, 0, 0]).startswith("0x00")


def test_bad_enum_alias_is_detected_as_catalogue_programming_error() -> None:
    """An alias pointing at no canonical enum label fails explicitly."""
    register = RegisterDef(
        "bad_enum",
        1,
        "holding",
        "bad enum",
        codec="enum",
        enum={0: "off"},
        enum_aliases={"auto": "automatic"},
    )
    with pytest.raises(RuntimeError, match="bad enum alias"):
        enum_reverse(register)


def test_deep_merge_replaces_scalars_without_mutating_inputs() -> None:
    """Recursive defaults merging isolates nested objects and replaces scalars."""
    defaults = {"nested": {"one": 1}, "scalar": 1}
    supplied = {"nested": {"two": 2}, "scalar": {"now": "mapping"}}
    merged = deep_merge(defaults, supplied)
    assert merged == {
        "nested": {"one": 1, "two": 2},
        "scalar": {"now": "mapping"},
    }
    merged["nested"]["one"] = 9
    assert defaults["nested"]["one"] == 1


async def test_config_store_requires_load_before_access_save_or_update(
    tmp_path: Path,
) -> None:
    """All stateful configuration operations fail clearly before loading."""
    store = ConfigStore(tmp_path / "config.json")
    with pytest.raises(ConfigError, match="not been loaded"):
        _ = store.data
    with pytest.raises(ConfigError, match="not been loaded"):
        await store.save()
    with pytest.raises(ConfigError, match="not been loaded"):
        await store.update_desired({"bypass_mode": "open"})


async def test_config_relative_paths_cover_disabled_relative_and_absolute(
    config_path: Path, tmp_path: Path
) -> None:
    """Configured output paths support disabling and both path forms."""
    store = ConfigStore(config_path)
    assert store.resolve_relative_path(None) is None
    assert store.resolve_relative_path(" ") is None
    assert store.resolve_relative_path("state.json") == tmp_path / "state.json"
    absolute = tmp_path / "absolute.json"
    assert store.resolve_relative_path(str(absolute)) == absolute


def test_atomic_write_removes_temporary_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Atomic persistence cleans its temporary file after an external OS failure."""
    import wolf_325.config as config_module

    def fail_replace(source: str, destination: Path) -> None:
        """Simulate an operating-system failure during atomic replacement."""
        raise OSError(f"cannot replace {source} with {destination}")

    monkeypatch.setattr(config_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="cannot replace"):
        atomic_json_write_sync(tmp_path / "config.json", {"x": 1})
    assert not list(tmp_path.glob("*.tmp"))


def test_normalization_allows_explicit_dangerous_nonpersistent_values() -> None:
    """Dangerous communication settings require but honor explicit opt-in."""
    assert normalize_settings(
        {"modbus_slave_address": 21}, allow_dangerous=True
    ) == {"modbus_slave_address": 21}
    with pytest.raises(RegisterError, match="must not be restored"):
        normalize_settings(
            {"device_time": "12:00"}, require_restorable=True
        )


async def test_profile_empty_directory_name_validation_and_parent_override(
    tmp_path: Path,
) -> None:
    """Profile listing and inheritance cover absent folders and child overrides."""
    absent = ProfileLoader(tmp_path / "absent")
    assert await absent.list_profiles() == []
    with pytest.raises(ProfileError, match="invalid profile name"):
        await absent.load("../escape")
    (tmp_path / "parent.json").write_text(
        json.dumps({"unset": ["bypass_mode"]}), encoding="utf-8"
    )
    (tmp_path / "child.json").write_text(
        json.dumps(
            {
                "extends": ["parent"],
                "settings": {"bypass_mode": "automatic"},
            }
        ),
        encoding="utf-8",
    )
    resolved = await ProfileLoader(tmp_path).load("child")
    assert resolved.unset == []
    assert resolved.settings == {"bypass_mode": "automatic"}


async def test_controller_double_start_background_stop_and_async_context(
    config_path: Path,
) -> None:
    """Lifecycle operations are idempotent and async context cleanup closes I/O."""
    instance = WolfCWL2(config_path)
    await instance.load_config()
    client = FakeClient()
    instance._client = client
    assert instance.get_value("filter_status", default="missing") == "missing"
    await instance.start(restore=False, background=True, read_only=True)
    assert len(instance._tasks) == 3
    await instance.start(restore=False, background=True, read_only=True)
    assert len(instance._tasks) == 3
    await instance.stop()
    assert instance.connected is False
    await instance.stop()


async def test_queue_overflow_retains_latest_update(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A bounded slow subscriber drops its oldest value and receives the latest."""
    instance, client = controller
    stream = instance.updates(queue_size=1)
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    client.input[4036] = 100
    await instance.refresh("supply_temperature_c")
    assert (await pending)["value"] == 10.0
    next_value = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    client.input[4036] = 110
    await instance.refresh("supply_temperature_c")
    assert (await next_value)["value"] == 11.0
    await stream.aclose()


async def test_mark_block_unavailable_updates_cached_error(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Failed optional blocks make their member values unavailable with context."""
    instance, client = controller
    client.input[4150] = 1
    await instance.refresh("geo_heat_exchanger_status")
    await instance._mark_block_unavailable(
        ReadBlock("input", "fast", 4150, 1, optional=True), "illegal address"
    )
    state = instance.get_state("geo_heat_exchanger_status")
    assert state["available"] is False
    assert state["error"] == "illegal address"
