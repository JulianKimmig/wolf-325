"""Behavior tests for polling, updates, writes, and desired-state control."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from wolf_325 import (
    BulkWriteError,
    CommunicationError,
    RegisterError,
    WolfCWL2,
)

from conftest import FakeClient


def test_unstarted_controller_exposes_explicit_empty_state(config_path: Path) -> None:
    """Every known value exists in cache but is unavailable before polling."""
    instance = WolfCWL2(config_path)
    snapshot = instance.snapshot()
    assert len(snapshot["values"]) == 156
    assert snapshot["connected"] is False
    assert snapshot["values"]["supply_temperature_c"]["available"] is False
    assert snapshot["values"]["supply_dew_point_c"]["available"] is False
    with pytest.raises(RegisterError):
        instance.get_value("does_not_exist")


async def test_refresh_decodes_value_and_updates_snapshot(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A named read decodes engineering units and populates cached state."""
    instance, client = controller
    client.input[4036] = 214
    value = await instance.refresh("supply_temperature_c")
    assert value == 21.4
    assert instance.get_value("supply_temperature_c") == 21.4
    public = instance.get_state("supply_temperature_c")
    assert public["raw"] == 214
    assert public["unit"] == "°C"
    assert public["updated_at"] is not None
    assert instance.snapshot(available_only=True)["values"] == {
        "supply_temperature_c": public
    }


async def test_callbacks_and_async_update_stream_receive_changes_only(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Subscribers receive copied updates only when observable state changes."""
    instance, client = controller
    received: list[dict[str, object]] = []
    instance.subscribe(received.append)
    stream = instance.updates(queue_size=2)
    next_update = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)
    client.input[4036] = 205
    await instance.refresh("supply_temperature_c")
    streamed = await asyncio.wait_for(next_update, timeout=1)
    assert received[0]["key"] == "supply_temperature_c"
    assert streamed["value"] == 20.5
    count = len(received)
    await instance.refresh("supply_temperature_c")
    assert len(received) == count
    await stream.aclose()


async def test_poll_once_reads_all_enabled_tiers_and_writes_state_file(
    controller: tuple[WolfCWL2, FakeClient], config_path: Path
) -> None:
    """One-shot polling visits every enabled block and persists the full cache."""
    instance, client = controller
    client.input[4036] = 193
    await instance.poll_once()
    assert {tier for tier in instance.snapshot()["last_poll_at"]} == {
        "fast",
        "slow",
        "static",
    }
    assert any(read[:3] == ("input", 4020, 5) for read in client.reads)
    assert any(read[:3] == ("holding", 6000, 4) for read in client.reads)
    state_path = config_path.parent / "state.json"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["values"]["supply_temperature_c"]["value"] == 19.3


async def test_polling_respects_holding_and_extension_switches(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Configuration can disable holding and extension-board block reads."""
    instance, client = controller
    assert instance.config is not None
    instance.config["polling"]["read_holding_registers"] = False
    instance.config["polling"]["read_extension_registers"] = False
    await instance.poll_once()
    assert all(table != "holding" for table, *_ in client.reads)
    extension_starts = {4150, 4500, 4520, 4541}
    assert all(address not in extension_starts for _, address, _, _ in client.reads)


async def test_named_setter_persists_before_writing_and_orders_remote_mode_last(
    controller: tuple[WolfCWL2, FakeClient], config_path: Path
) -> None:
    """Remote level owns target and mode, persisting both before ordered writes."""
    instance, client = controller
    result = await instance.set_ventilation_level("high")
    assert result == {
        "remote_ventilation_level": "high",
        "remote_control_mode": "level",
    }
    assert [address for address, _, _ in client.writes] == [8001, 8000]
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["desired"]["remote_ventilation_level"] == "high"
    assert saved["desired"]["remote_control_mode"] == "level"


async def test_specialized_setters_cover_airflow_standby_bypass_and_presets(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Convenience setters map to the same validated named settings API."""
    instance, client = controller
    assert await instance.set_airflow(180) == {
        "remote_airflow_m3h": 180,
        "remote_control_mode": "airflow",
    }
    assert await instance.set_standby(True) is True
    assert await instance.set_standby(False) is False
    assert await instance.set_bypass_mode("auto") == "automatic"
    presets = await instance.set_flow_presets(holiday=50, low=100, normal=175, high=300)
    assert presets["flow_preset_normal_m3h"] == 175
    assert client.holding[8002] == 180
    assert client.holding[8003] == 0


async def test_temporary_write_does_not_change_desired_configuration(
    controller: tuple[WolfCWL2, FakeClient], config_path: Path
) -> None:
    """Temporary settings affect the appliance without claiming persistent ownership."""
    instance, _ = controller
    await instance.set_setting("bypass_mode", "open", persist=False)
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["desired"] == {}


async def test_offline_persistent_setting_remains_queued(
    controller: tuple[WolfCWL2, FakeClient], config_path: Path
) -> None:
    """A failed external write preserves already-persisted desired state for retry."""
    instance, client = controller
    client.fail_writes = True
    with pytest.raises(BulkWriteError):
        await instance.set_setting("bypass_mode", "open")
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["desired"]["bypass_mode"] == "open"


async def test_bulk_write_reports_partial_results_and_can_return_errors(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Bulk operations retain successful results and expose per-setting failures."""
    instance, client = controller
    client.fail_writes = True
    with pytest.raises(BulkWriteError) as captured:
        await instance.set_settings({"bypass_mode": "open", "remote_standby": False})
    assert captured.value.errors
    client.connected = True
    instance._client = client
    result = await instance.set_settings(
        {"bypass_mode": "open"}, persist=False, raise_on_error=False
    )
    assert result == {}


async def test_read_only_mode_rejects_writes_and_skips_desired_apply(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Read-only startup provides a hard write guard including reconciliation."""
    instance, client = controller
    instance._read_only = True
    with pytest.raises(RegisterError, match="read-only"):
        await instance.set_setting("bypass_mode", "open")
    assert await instance.apply_desired(force=True) == {
        "written": {},
        "skipped": {},
        "errors": {},
    }
    assert client.writes == []


async def test_apply_desired_skips_matching_values_and_force_rewrites(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Reconciliation avoids matching writes while restoration rewrites everything."""
    instance, client = controller
    await instance.set_setting("bypass_mode", "automatic")
    client.writes.clear()
    result = await instance.apply_desired(force=False)
    assert result["skipped"] == {"bypass_mode": "automatic"}
    assert client.writes == []
    forced = await instance.apply_desired(force=True)
    assert forced["written"] == {"bypass_mode": "automatic"}
    assert [address for address, _, _ in client.writes] == [6100]


async def test_startup_force_restores_desired_values_in_safe_order(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Startup restoration rewrites targets before selecting their control mode."""
    instance, client = controller
    await instance.set_ventilation_level("normal")
    client.writes.clear()
    client.holding[8000] = 0
    client.holding[8001] = 0
    await instance.start(restore=True, background=False)
    addresses = [address for address, _, _ in client.writes]
    assert addresses.index(8001) < addresses.index(8000)


async def test_profile_application_is_partial_and_persistent(
    controller: tuple[WolfCWL2, FakeClient], config_path: Path
) -> None:
    """Applying a partial profile retains unrelated desired settings and records it."""
    instance, _ = controller
    profile = config_path.parent / "profiles" / "night.json"
    profile.write_text(
        json.dumps(
            {
                "settings": {
                    "remote_ventilation_level": "low",
                    "remote_control_mode": "level",
                    "remote_standby": False,
                }
            }
        ),
        encoding="utf-8",
    )
    await instance.set_setting("bypass_mode", "automatic")
    await instance.apply_profile("night")
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["desired"]["bypass_mode"] == "automatic"
    assert saved["desired"]["remote_ventilation_level"] == "low"
    assert saved["last_profile"] == "night"


async def test_one_shot_resets_use_guarded_raw_commands(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Dedicated reset methods send action words and guard appliance reset."""
    instance, client = controller
    assert await instance.reset_filter_warning() == "executed"
    with pytest.raises(RegisterError, match="confirm"):
        await instance.reset_appliance(confirm=False)
    assert await instance.reset_appliance(
        confirm=True
    ) == "command_sent; the appliance may disconnect while rebooting"
    assert (8010, 1, 20) in client.writes
    assert (8011, 1, 20) in client.writes


async def test_failed_read_surfaces_communication_error_and_disconnects(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """External transport failures invalidate the client and surface a domain error."""
    instance, client = controller
    client.fail_reads = True
    with pytest.raises(CommunicationError):
        await instance.refresh("supply_temperature_c")
    assert instance.connected is False


async def test_verification_failure_reports_written_and_actual_values(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Write verification fails explicitly when read-back never matches."""
    instance, client = controller
    client.holding[6100] = 0

    async def ignore_write(
        address: int, value: int, *, device_id: int = 1, **_: object
    ) -> object:
        client.writes.append((address, value, device_id))
        from conftest import FakeResponse

        return FakeResponse()

    client.write_register = ignore_write  # type: ignore[method-assign]
    assert instance.config is not None
    instance.config["persistence"]["verify_attempts"] = 1
    with pytest.raises(BulkWriteError) as captured:
        await instance.set_setting("bypass_mode", "open", persist=False)
    assert "read back" in captured.value.errors["bypass_mode"]
