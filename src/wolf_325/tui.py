"""Standalone command-line entry point for the interactive controller TUI."""

from __future__ import annotations

import argparse
import logging
import math
from collections.abc import Sequence
from pathlib import Path


def _positive_float(text: str) -> float:
    """Parse a strictly positive floating-point command-line value.

    Args:
        text: Raw argument text supplied by argparse.

    Returns:
        Parsed positive number.

    Raises:
        argparse.ArgumentTypeError: If the value is not positive.
    """
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return value


def build_parser() -> argparse.ArgumentParser:
    """Build the public argument parser for ``wolf-cwl2-tui``.

    Returns:
        Configured argument parser without parsing process arguments.
    """
    parser = argparse.ArgumentParser(
        prog="wolf-cwl2-tui",
        description="Interactive monitor and controller for a WOLF CWL-2 appliance",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("wolf_cwl2_config.json"),
        help="controller JSON configuration (default: %(default)s)",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="monitor the device while disabling every write and profile action",
    )
    parser.add_argument(
        "--refresh-interval",
        type=_positive_float,
        default=1.0,
        metavar="SECONDS",
        help="table redraw interval (default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="WARNING",
        help="controller log level (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse options and run the Textual application until it exits.

    Args:
        argv: Optional argument sequence; process arguments are used when absent.

    Returns:
        Process exit status returned after a normal UI shutdown.
    """
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    from .tui_app import WolfCWL2App

    app = WolfCWL2App(
        config_path=args.config.expanduser().resolve(),
        read_only=args.read_only,
        refresh_interval=args.refresh_interval,
    )
    app.run()
    return 0


__all__ = ["build_parser", "main"]
