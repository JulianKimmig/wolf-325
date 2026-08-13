"""Extended CLI dispatch tests using the real controller and external simulator."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from wolf_325 import WolfCWL2
from wolf_325.cli import (
    _catalogue_json,
    _parse_cli_value,
    _profile_as_json,
    _run_device_command,
    _run_local_command,
    build_parser,
    main,
)
from wolf_325.profiles import ResolvedProfile

from conftest import FakeClient


@pytest.mark.parametrize(
    ("text", "expected"),
    [("true", True), ("17", 17), ('"open"', "open"), ("automatic", "automatic")],
)
def test_cli_value_parser_preserves_json_types_or_enum_text(
    text: str, expected: object
) -> None:
    """CLI setting values decode JSON scalars without rejecting plain enum labels."""
    assert _parse_cli_value(text) == expected


def test_profile_json_projection_and_catalogue_metadata() -> None:
    """CLI projections expose resolved sources and complete setting constraints."""
    profile = ResolvedProfile(
        name="night",
        description="quiet",
        settings={"bypass_mode": "open"},
        unset=["remote_standby"],
        replace=False,
        sources=["base", "night"],
    )
    assert _profile_as_json(profile)["extends_resolved"] == ["base", "night"]
    catalogue = _catalogue_json(writable_only=False)
    assert catalogue["bypass_mode"]["allowed"] == ["automatic", "closed", "open"]
    assert catalogue["bypass_indoor_threshold_c"]["step"] == 0.5


async def test_local_cli_dispatch_lists_previews_and_prints_desired(
    config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Config-only CLI commands use the real profile/config services without I/O."""
    profile = config_path.parent / "profiles" / "night.json"
    profile.write_text(
        json.dumps({"description": "quiet", "settings": {"bypass": "open"}}),
        encoding="utf-8",
    )
    parser = build_parser()
    for arguments in (["profiles"], ["preview-profile", "night"], ["desired"]):
        controller = WolfCWL2(config_path)
        args = parser.parse_args(arguments)
        assert await _run_local_command(args, controller) is True
        assert capsys.readouterr().out
    controller = WolfCWL2(config_path)
    assert await _run_local_command(parser.parse_args(["snapshot"]), controller) is False


async def test_local_cli_saves_derived_profile_without_device_io(
    config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The save-profile command writes and reports a delta from the active profile."""
    profile = config_path.parent / "profiles" / "normal.json"
    profile.write_text(
        json.dumps(
            {
                "settings": {
                    "remote_control_mode": "level",
                    "remote_ventilation_level": "normal",
                }
            }
        ),
        encoding="utf-8",
    )
    controller = WolfCWL2(config_path)
    await controller.load_config()
    desired = await controller.config_store.update_desired(
        {
            "remote_control_mode": "level",
            "remote_ventilation_level": "high",
        },
        replace=True,
        last_profile="normal",
    )
    controller.config["desired"] = desired
    controller.config["last_profile"] = "normal"
    args = build_parser().parse_args(
        ["save-profile", "party", "--description", "Party ventilation"]
    )

    assert await _run_local_command(args, controller) is True

    output = json.loads(capsys.readouterr().out)
    assert output["name"] == "party"
    assert output["extends"] == "normal"
    assert output["settings"] == {"remote_ventilation_level": "high"}
    document = json.loads(
        (config_path.parent / "profiles" / "party.json").read_text(encoding="utf-8")
    )
    assert document["extends"] == "normal"
    assert controller.config["last_profile"] == "normal"
    assert controller.desired == {
        "remote_control_mode": "level",
        "remote_ventilation_level": "high",
    }


@pytest.mark.parametrize(
    ("arguments", "expected_key", "expected_value"),
    [
        (["set", "bypass", "open", "--temporary"], "bypass_mode", "open"),
        (["level", "high", "--temporary"], "remote_ventilation_level", "high"),
        (["airflow", "180", "--temporary"], "remote_airflow_m3h", 180),
        (["standby", "on", "--temporary"], "remote_standby", True),
        (["bypass", "closed", "--temporary"], "bypass_mode", "closed"),
    ],
)
async def test_device_cli_write_dispatch_uses_real_controller(
    controller: tuple[WolfCWL2, FakeClient],
    arguments: list[str],
    expected_key: str,
    expected_value: object,
) -> None:
    """Each convenience command dispatches through actual validated controller writes."""
    instance, _ = controller
    result = await _run_device_command(build_parser().parse_args(arguments), instance)
    assert result[expected_key] == expected_value


async def test_device_cli_snapshot_get_profile_and_reset_dispatch(
    controller: tuple[WolfCWL2, FakeClient], config_path: Path
) -> None:
    """Remaining device commands return their documented JSON or action values."""
    instance, client = controller
    parser = build_parser()
    client.input[4100] = 1
    assert "values" in await _run_device_command(
        parser.parse_args(["snapshot", "--available-only"]), instance
    )
    state = await _run_device_command(parser.parse_args(["get", "filter_status"]), instance)
    assert state["value"] == "dirty"
    profile = config_path.parent / "profiles" / "night.json"
    profile.write_text(
        json.dumps({"settings": {"bypass_mode": "automatic"}}),
        encoding="utf-8",
    )
    applied = await _run_device_command(
        parser.parse_args(["profile", "night", "--temporary"]), instance
    )
    assert applied == {"bypass_mode": "automatic"}
    assert await _run_device_command(
        parser.parse_args(["reset-filter"]), instance
    ) == "executed"


def test_main_prints_config_only_desired(config_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Top-level execution handles desired state without opening a device connection."""
    assert main(["--config", str(config_path), "desired"]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_main_saves_standalone_profile_without_connecting_device(
    config_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The public CLI entry point captures desired state as a local-only command."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["desired"] = {
        "remote_control_mode": "airflow",
        "remote_airflow_m3h": 170,
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = main(
        [
            "--config",
            str(config_path),
            "save-profile",
            "captured",
            "--description",
            "Captured from CLI",
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["name"] == "captured"
    assert output["extends"] is None
    assert (config_path.parent / "profiles" / "captured.json").exists()


def test_module_entrypoint_delegates_to_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Running the package module invokes the same non-network register command."""
    monkeypatch.setattr(sys, "argv", ["python -m wolf_325", "registers", "--writable-only"])
    with pytest.raises(SystemExit) as captured:
        runpy.run_module("wolf_325.__main__", run_name="__main__")
    assert captured.value.code == 0
    assert len(json.loads(capsys.readouterr().out)) == 78
