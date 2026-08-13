"""CLI for querying repository rules by Boolean tag expressions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from search_metadata import find_rules_root, load_rule_headers
from search_output import format_query_markdown, match_to_dict
from search_query import QueryError, RuleMatch, query_rule_headers


def main() -> int:
    """Run the command-line entrypoint.

    Returns:
        Process exit code.
    """
    return run(sys.argv[1:], sys.stdout, sys.stderr)


def run(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    """Run rule query mode.

    Args:
        argv: Command-line arguments after the executable name.
        stdout: Stream for query output.
        stderr: Stream for diagnostics.

    Returns:
        Process exit code.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        root = Path(args.root).resolve() if args.root else _query_root()
        matches = query_rule_headers(root, args.tags, include_manual=args.include_manual)
        _write_output(root, matches, args.format, stdout, stderr)
    except (QueryError, ValueError) as exc:
        stderr.write(f"rule query failed: {exc}\n")
        return 1
    return 0


def _write_output(
    root: Path,
    matches: list[RuleMatch],
    output_format: str,
    stdout: TextIO,
    stderr: TextIO,
) -> None:
    """Write query matches and diagnostics.

    Args:
        root: Repository root containing ``.rules``.
        matches: Rule matches to write.
        output_format: Either ``json`` or ``markdown``.
        stdout: Stream for query output.
        stderr: Stream for malformed rule diagnostics in Markdown mode.
    """
    _headers, skipped = load_rule_headers(root)
    if output_format == "json":
        payload: dict[str, Any] = {
            "rules": [match_to_dict(match) for match in matches],
            "skipped": [
                {"path": skipped_rule.path, "reason": skipped_rule.reason}
                for skipped_rule in skipped
            ],
        }
        json.dump(payload, stdout)
        stdout.write("\n")
        return
    stdout.write(format_query_markdown(matches))
    if skipped:
        stderr.write(_format_warning(skipped) + "\n")


def _query_root() -> Path:
    """Return the repository root for an explicit query command.

    Returns:
        Repository root containing ``.rules``.
    """
    cwd = Path(os.getcwd()).resolve()
    root = find_rules_root(cwd)
    if root is None:
        raise ValueError("no .rules directory found")
    return root


def _build_parser() -> argparse.ArgumentParser:
    """Build the repo rule query argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(prog="query_rules.py")
    parser.add_argument("--tags", required=True, help="Boolean tag expression")
    parser.add_argument("--root", help="Repository root containing .rules")
    parser.add_argument(
        "--include-manual",
        action="store_true",
        help="Include visibility=never/manual rules",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Reduced header output format",
    )
    return parser


def _format_warning(skipped: list[object]) -> str:
    """Format skipped rule diagnostics for query warnings.

    Args:
        skipped: Malformed rule diagnostics.

    Returns:
        Single-line warning.
    """
    count = len(skipped)
    noun = "rule" if count == 1 else "rules"
    details = "; ".join(
        f"{skipped_rule.path}: {skipped_rule.reason}" for skipped_rule in skipped
    )
    return f"Skipped {count} malformed local {noun}: {details}"


if __name__ == "__main__":
    raise SystemExit(main())
