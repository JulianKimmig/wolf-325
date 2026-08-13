"""Inject bounded local rule context during Codex hook startup."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from rule_metadata import find_rules_root, load_rule_headers
from rule_output import format_bootstrap_context


def main() -> int:
    """Run the command-line entrypoint.

    Returns:
        Process exit code expected by Codex command hooks.
    """
    return run(sys.argv[1:], sys.stdin.read(), sys.stdout, sys.stderr)


def run(argv: list[str], raw_stdin: str, stdout: TextIO, stderr: TextIO) -> int:
    """Run hook mode.

    Args:
        argv: Command-line arguments after the executable name. The hook does
            not accept command arguments.
        raw_stdin: Raw hook stdin text.
        stdout: Stream for command output.
        stderr: Stream for diagnostics.

    Returns:
        Process exit code.
    """
    if argv:
        stderr.write("rules_context hook does not accept arguments\n")
        return 1
    try:
        return _run_hook(raw_stdin, stdout, stderr)
    except ValueError as exc:
        stderr.write(f"rules_context hook failed: {exc}\n")
        return 1


def _run_hook(raw_stdin: str, stdout: TextIO, stderr: TextIO) -> int:
    """Run Codex hook mode and write a JSON hook response."""
    try:
        payload = _read_hook_payload(raw_stdin)
        event_name = str(payload.get("hook_event_name", "SessionStart"))
        cwd = Path(str(payload.get("cwd", os.getcwd()))).resolve()
        root = find_rules_root(cwd) or Path(__file__).parents[3]
        headers, skipped = load_rule_headers(root)
        output = {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": format_bootstrap_context(headers, skipped),
            }
        }
        if skipped:
            output["systemMessage"] = _format_warning(skipped)
        json.dump(output, stdout)
        stdout.write("\n")
    except Exception as exc:
        stderr.write(f"rules_context hook failed: {exc}\n")
        return 1
    return 0


def _read_hook_payload(raw_stdin: str) -> dict[str, Any]:
    """Parse a Codex hook JSON payload.

    Args:
        raw_stdin: Raw hook stdin text.

    Returns:
        Parsed JSON object, or an empty object when stdin is empty.
    """
    if not raw_stdin.strip():
        return {}
    payload = json.loads(raw_stdin)
    if not isinstance(payload, dict):
        raise ValueError("hook stdin must be a JSON object")
    return payload


def _format_warning(skipped: list[object]) -> str:
    """Format skipped rule diagnostics for hook warnings."""
    count = len(skipped)
    noun = "rule" if count == 1 else "rules"
    details = "; ".join(
        f"{skipped_rule.path}: {skipped_rule.reason}" for skipped_rule in skipped
    )
    return f"Skipped {count} malformed local {noun}: {details}"


if __name__ == "__main__":
    raise SystemExit(main())
