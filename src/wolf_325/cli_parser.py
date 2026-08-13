"""Argument parser construction for the packaged wolf-cwl2 command."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build and return the complete public command-line parser."""
    parser = argparse.ArgumentParser(
        description="Async WOLF CWL-2-325 Modbus controller"
    )
    parser.add_argument(
        "--config", default="wolf_cwl2_config.json", help="JSON configuration path"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser(
        "init-config", help="create a new configuration and example profiles"
    )
    initialize.add_argument(
        "--host", default="192.168.1.200", help="gateway IP address"
    )
    initialize.add_argument(
        "--force", action="store_true", help="overwrite an existing config"
    )

    run = commands.add_parser("run", help="run continuously")
    run.add_argument(
        "--read-only", action="store_true", help="disable restoration and writes"
    )
    run.add_argument(
        "--print-updates", action="store_true", help="print changed JSON values"
    )
    snapshot = commands.add_parser(
        "snapshot", help="read all documented values once and print JSON"
    )
    snapshot.add_argument("--available-only", action="store_true")
    get = commands.add_parser("get", help="read one named value")
    get.add_argument("name")
    set_command = commands.add_parser("set", help="set any named writable parameter")
    set_command.add_argument("name")
    set_command.add_argument("value", help="JSON scalar or enum text")
    set_command.add_argument("--temporary", action="store_true")
    level = commands.add_parser("level", help="select holiday/low/normal/high")
    level.add_argument("value", choices=("holiday", "low", "normal", "high"))
    level.add_argument("--temporary", action="store_true")
    airflow = commands.add_parser("airflow", help="set direct airflow in m³/h")
    airflow.add_argument("value", type=int)
    airflow.add_argument("--temporary", action="store_true")
    standby = commands.add_parser("standby", help="enter or leave standby")
    standby.add_argument("value", choices=("on", "off"))
    standby.add_argument("--temporary", action="store_true")
    bypass = commands.add_parser("bypass", help="set automatic/closed/open bypass")
    bypass.add_argument("value", choices=("automatic", "closed", "open"))
    bypass.add_argument("--temporary", action="store_true")
    commands.add_parser("profiles", help="list profile files")
    preview = commands.add_parser(
        "preview-profile", help="resolve a profile without applying it"
    )
    preview.add_argument("name")
    profile = commands.add_parser("profile", help="apply a profile")
    profile.add_argument("name")
    profile.add_argument("--temporary", action="store_true")
    profile.add_argument("--replace", action="store_true")
    save_profile = commands.add_parser(
        "save-profile",
        help="save persistent desired changes as a new derived profile",
    )
    save_profile.add_argument("name", help="new profile name without .json")
    save_profile.add_argument(
        "--description", default="", help="human-readable profile description"
    )
    save_profile.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing profile with the same name",
    )
    commands.add_parser("desired", help="print persistent desired settings")
    registers = commands.add_parser(
        "registers", help="print the built-in register catalogue"
    )
    registers.add_argument("--writable-only", action="store_true")
    commands.add_parser("reset-filter", help="send one-shot filter warning reset")
    reset_appliance = commands.add_parser(
        "reset-appliance", help="send one-shot appliance reset"
    )
    reset_appliance.add_argument("--yes", action="store_true")
    return parser
