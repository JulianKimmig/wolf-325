"""Behavior tests for public command-line parsing and local-only commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wolf_325.cli import build_parser, main


def test_parser_exposes_reference_commands_and_common_options() -> None:
    """The packaged CLI retains every command advertised by the guide."""
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert set(commands) == {
        "init-config",
        "run",
        "snapshot",
        "get",
        "set",
        "level",
        "airflow",
        "standby",
        "bypass",
        "profiles",
        "preview-profile",
        "profile",
        "save-profile",
        "desired",
        "registers",
        "reset-filter",
        "reset-appliance",
    }
    parsed = parser.parse_args(["--config", "custom.json", "set", "bypass", "open"])
    assert parsed.config == "custom.json"
    assert parsed.name == "bypass"
    assert parsed.value == "open"


def test_init_config_creates_config_and_example_profiles(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Initialization produces a usable config plus all documented profile examples."""
    config = tmp_path / "wolf.json"
    assert main(["--config", str(config), "init-config", "--host", "192.0.2.10"]) == 0
    payload = json.loads(config.read_text(encoding="utf-8"))
    assert payload["connection"]["host"] == "192.0.2.10"
    assert {path.name for path in (tmp_path / "profiles").glob("*.json")} == {
        "normal.json",
        "night.json",
        "boost.json",
        "away.json",
        "summer-night.json",
    }
    assert "created" in capsys.readouterr().out


def test_init_config_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """Initialization protects existing user configuration by default."""
    config = tmp_path / "wolf.json"
    config.write_text("{}", encoding="utf-8")
    assert main(["--config", str(config), "init-config"]) == 2


def test_registers_command_outputs_complete_catalogue(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The register catalogue can be inspected without a config or live device."""
    assert main(["registers"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 154
    assert output["supply_temperature_c"]["address"] == 4036
    assert output["supply_temperature_c"]["writable"] is False


def test_writable_register_filter_contains_only_write_targets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The writable catalogue filter excludes read-only telemetry."""
    assert main(["registers", "--writable-only"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 78
    assert "bypass_mode" in output
    assert "supply_temperature_c" not in output
