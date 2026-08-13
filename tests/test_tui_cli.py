"""Behavior tests for the standalone controller TUI entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from wolf_325.tui import build_parser


def test_tui_parser_exposes_config_safety_and_refresh_options() -> None:
    """Operators can choose configuration, read-only safety, and UI cadence."""
    args = build_parser().parse_args(
        ["--config", "unit.json", "--read-only", "--refresh-interval", "0.25"]
    )

    assert args.config == Path("unit.json")
    assert args.read_only is True
    assert args.refresh_interval == 0.25


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_tui_parser_rejects_invalid_refresh_interval(value: str) -> None:
    """Nonpositive and non-finite redraw cadences are rejected by argparse."""
    parser = build_parser()

    try:
        parser.parse_args(["--refresh-interval", value])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("parser accepted a nonpositive refresh interval")
