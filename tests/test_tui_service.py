"""Controller-backed behavior tests for TUI operations and safety guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wolf_325.errors import RegisterError
from wolf_325.tui_service import ControllerTuiService


@pytest.mark.asyncio
async def test_service_writes_normalized_temporary_value_through_controller(
    controller: tuple[object, object],
) -> None:
    """A normal editor submission uses the real controller write pipeline."""
    instance, client = controller
    service = ControllerTuiService(instance, read_only=False)  # type: ignore[arg-type]
    await service.start(background=False)

    result = await service.write_register(
        "remote_airflow_m3h", "200", persist=False, confirmation=None
    )

    assert result == 200
    assert (8002, 200, 20) in client.writes  # type: ignore[attr-defined]
    assert instance.desired == {}  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_service_persists_restorable_value_and_can_release_it(
    controller: tuple[object, object],
) -> None:
    """Persistent ownership is visible and explicitly releasable from the TUI."""
    instance, _ = controller
    service = ControllerTuiService(instance, read_only=False)  # type: ignore[arg-type]
    await service.start(background=False)

    await service.write_register(
        "remote_airflow_m3h", "170", persist=True, confirmation=None
    )
    assert instance.desired["remote_airflow_m3h"] == 170  # type: ignore[attr-defined]

    await service.release_desired("remote_airflow_m3h")
    assert instance.desired == {}  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_service_blocks_read_only_and_unconfirmed_dangerous_writes(
    controller: tuple[object, object],
) -> None:
    """Safety mode and confirmation phrases prevent external writes."""
    instance, client = controller
    await ControllerTuiService(instance, read_only=True).start(background=False)  # type: ignore[arg-type]
    read_only = ControllerTuiService(instance, read_only=True)  # type: ignore[arg-type]

    with pytest.raises(RegisterError, match="read-only"):
        await read_only.write_register(
            "remote_airflow_m3h", "100", persist=False, confirmation=None
        )
    with pytest.raises(RegisterError, match="RESET APPLIANCE"):
        await ControllerTuiService(instance, read_only=False).write_register(  # type: ignore[arg-type]
            "appliance_reset_status",
            "",
            persist=False,
            confirmation="reset appliance",
        )
    assert client.writes == []  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_service_dispatches_guarded_one_shot_actions(
    controller: tuple[object, object],
) -> None:
    """One-shot editors call their dedicated controller APIs after confirmation."""
    instance, client = controller
    service = ControllerTuiService(instance, read_only=False)  # type: ignore[arg-type]
    await service.start(background=False)

    result = await service.write_register(
        "filter_reset_status",
        "",
        persist=False,
        confirmation="EXECUTE ACTION",
    )

    assert result == "executed"
    assert (8010, 1, 20) in client.writes  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_service_previews_and_applies_profiles(
    controller: tuple[object, object], config_path: Path
) -> None:
    """Profile menus expose resolved settings before applying them."""
    profile_path = config_path.parent / "profiles" / "quiet.json"
    profile_path.write_text(
        json.dumps(
            {
                "description": "Quiet direct airflow",
                "settings": {
                    "remote_airflow_m3h": 100,
                    "remote_control_mode": "airflow",
                },
            }
        ),
        encoding="utf-8",
    )
    instance, client = controller
    service = ControllerTuiService(instance, read_only=False)  # type: ignore[arg-type]
    await service.start(background=False)

    assert await service.list_profiles() == ["quiet"]
    preview = await service.preview_profile("quiet")
    assert "Quiet direct airflow" in preview
    assert "remote_airflow_m3h = 100" in preview

    await service.apply_profile("quiet", persist=False)
    assert (8002, 100, 20) in client.writes  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_service_previews_and_saves_current_profile_changes(
    controller: tuple[object, object], config_path: Path
) -> None:
    """The TUI adapter exposes derived-profile preview and atomic save operations."""
    base_path = config_path.parent / "profiles" / "base.json"
    base_path.write_text(
        json.dumps({"settings": {"remote_airflow_m3h": 100}}),
        encoding="utf-8",
    )
    instance, _ = controller
    desired = await instance.config_store.update_desired(  # type: ignore[attr-defined]
        {"remote_airflow_m3h": 170}, replace=True, last_profile="base"
    )
    instance.config["desired"] = desired  # type: ignore[index]
    instance.config["last_profile"] = "base"  # type: ignore[index]
    service = ControllerTuiService(instance, read_only=False)  # type: ignore[arg-type]

    preview = await service.preview_profile_capture()
    saved = await service.save_profile(
        "custom", description="Custom airflow", overwrite=False
    )

    assert "Base profile: base" in preview
    assert "remote_airflow_m3h = 170" in preview
    assert saved.name == "custom"
    assert (config_path.parent / "profiles" / "custom.json").exists()


@pytest.mark.asyncio
async def test_read_only_service_blocks_profile_capture(
    controller: tuple[object, object],
) -> None:
    """Read-only TUI mode prevents local profile file creation as well as device I/O."""
    instance, _ = controller
    service = ControllerTuiService(instance, read_only=True)  # type: ignore[arg-type]

    with pytest.raises(RegisterError, match="read-only"):
        await service.save_profile("blocked", description="", overwrite=False)
