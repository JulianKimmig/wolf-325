"""Command-line execution for local inspection and WOLF appliance control."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import signal
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .catalogue import REGISTERS, resolve_register_name
from .cli_init import initialize_config
from .cli_parser import build_parser
from .controller import WolfCWL2
from .errors import BulkWriteError, WolfError
from .profiles import ResolvedProfile, SavedProfile

LOGGER = logging.getLogger("wolf_325")


def _parse_cli_value(text: str) -> Any:
    """Parse a JSON scalar when possible and otherwise preserve enum text."""
    stripped = text.strip()
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(stripped)
    return stripped


def _profile_as_json(profile: ResolvedProfile) -> dict[str, Any]:
    """Return the stable CLI JSON projection of a resolved profile."""
    return {
        "name": profile.name,
        "description": profile.description,
        "extends_resolved": profile.sources,
        "replace": profile.replace,
        "unset": profile.unset,
        "settings": profile.settings,
    }


def _saved_profile_as_json(profile: SavedProfile) -> dict[str, Any]:
    """Return the stable CLI JSON projection of a captured profile."""
    return {
        "name": profile.name,
        "path": str(profile.path),
        "description": profile.description,
        "extends": profile.changes.extends,
        "replace": profile.changes.replace,
        "unset": list(profile.changes.unset),
        "settings": profile.changes.settings,
    }


def _catalogue_json(*, writable_only: bool) -> dict[str, Any]:
    """Build the inspectable JSON catalogue, optionally restricted to writes."""
    catalogue: dict[str, Any] = {}
    for key, register in sorted(
        REGISTERS.items(), key=lambda item: (item[1].table, item[1].address)
    ):
        if writable_only and not register.writable:
            continue
        catalogue[key] = {
            "address": register.address,
            "table": register.table,
            "description": register.description,
            "unit": register.unit,
            "writable": register.writable,
            "restorable": register.restorable,
            "dangerous": register.dangerous,
            "one_shot": register.one_shot,
            "poll": register.poll,
            "allowed": list(register.enum.values()) if register.enum else None,
            "minimum": register.minimum,
            "maximum": register.maximum,
            "step": register.step,
            "extra_values": list(register.extra_values),
        }
    return catalogue


async def _run_local_command(args: argparse.Namespace, controller: WolfCWL2) -> bool:
    """Run config-only commands and return whether the command was handled."""
    if args.command not in {
        "profiles",
        "preview-profile",
        "save-profile",
        "desired",
    }:
        return False
    await controller.load_config()
    if args.command == "profiles":
        value: Any = await controller.list_profiles()
    elif args.command == "preview-profile":
        value = _profile_as_json(await controller.preview_profile(args.name))
    elif args.command == "save-profile":
        value = _saved_profile_as_json(
            await controller.save_profile(
                args.name,
                description=args.description,
                overwrite=args.overwrite,
            )
        )
    else:
        value = controller.desired
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return True


async def _run_daemon(args: argparse.Namespace, controller: WolfCWL2) -> int:
    """Run polling and reconciliation until an interrupt signal is received."""
    if args.print_updates:
        controller.subscribe(
            lambda update: print(json.dumps(update, ensure_ascii=False), flush=True)
        )
    await controller.start(read_only=args.read_only, background=True)
    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, shutdown.set)
    LOGGER.info("controller running; press Ctrl-C to stop")
    await shutdown.wait()
    await controller.stop()
    return 0


async def _run_device_command(
    args: argparse.Namespace, controller: WolfCWL2
) -> Any:
    """Run one read or write command against an initialized controller."""
    if args.command == "snapshot":
        return controller.snapshot(available_only=args.available_only)
    if args.command == "get":
        await controller.refresh(args.name)
        return controller.get_state(args.name)
    if args.command == "set":
        result = await controller.set_setting(
            args.name, _parse_cli_value(args.value), persist=not args.temporary
        )
        return {resolve_register_name(args.name): result}
    if args.command == "level":
        return await controller.set_ventilation_level(
            args.value, persist=not args.temporary
        )
    if args.command == "airflow":
        return await controller.set_airflow(args.value, persist=not args.temporary)
    if args.command == "standby":
        return {
            "remote_standby": await controller.set_standby(
                args.value == "on", persist=not args.temporary
            )
        }
    if args.command == "bypass":
        return {
            "bypass_mode": await controller.set_bypass_mode(
                args.value, persist=not args.temporary
            )
        }
    if args.command == "profile":
        return await controller.apply_profile(
            args.name,
            persist=not args.temporary,
            replace=True if args.replace else None,
        )
    if args.command == "reset-filter":
        return await controller.reset_filter_warning()
    if args.command == "reset-appliance":
        return await controller.reset_appliance(confirm=args.yes)
    raise RuntimeError(f"unhandled command {args.command}")


async def _run_cli(args: argparse.Namespace) -> int:
    """Dispatch a parsed command and return its process exit code."""
    config_path = Path(args.config).expanduser().resolve()
    if args.command == "init-config":
        await initialize_config(config_path, args.host, args.force)
        return 0
    if args.command == "registers":
        print(json.dumps(_catalogue_json(writable_only=args.writable_only), indent=2))
        return 0
    controller = WolfCWL2(config_path)
    if await _run_local_command(args, controller):
        return 0
    if args.command == "run":
        return await _run_daemon(args, controller)
    read_only = args.command in {"snapshot", "get"}
    await controller.start(
        restore=not read_only,
        background=False,
        read_only=read_only,
    )
    try:
        result = await _run_device_command(args, controller)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        await controller.stop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments, execute them, and translate domain failures."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return asyncio.run(_run_cli(args))
    except KeyboardInterrupt:
        return 130
    except WolfError as exc:
        LOGGER.error("%s", exc)
        if isinstance(exc, BulkWriteError):
            LOGGER.error("partial results: %s", exc.results)
            LOGGER.error("errors: %s", exc.errors)
        return 2


__all__ = ["build_parser", "main"]
