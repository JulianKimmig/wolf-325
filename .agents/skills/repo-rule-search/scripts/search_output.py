"""Output formatting for the repository rule search skill."""

from __future__ import annotations

from search_metadata import RuleHeader
from search_query import RuleMatch


def format_query_markdown(matches: list[RuleMatch]) -> str:
    """Format query matches as Markdown.

    Args:
        matches: Matched rule headers.

    Returns:
        Markdown reduced header output.
    """
    lines = ["## Matching Local Rules", ""]
    if not matches:
        lines.append("No matching local rules found.")
        return "\n".join(lines) + "\n"
    for match in matches:
        lines.extend(_format_header_lines(match.header))
        if not match.reason.startswith("matched tag query"):
            lines.append(f"  reason: {match.reason}")
    return "\n".join(lines) + "\n"


def match_to_dict(match: RuleMatch) -> dict[str, object]:
    """Convert a match to a JSON-serializable reduced header.

    Args:
        match: Matched rule header and reason.

    Returns:
        JSON-compatible mapping.
    """
    header = match.header
    return {
        "path": header.path,
        "name": header.name,
        "description": header.description,
        "apply": header.apply,
        "tags": list(header.tags),
        "visibility": header.visibility,
        "reason": match.reason,
    }


def _format_header_lines(header: RuleHeader) -> list[str]:
    """Format one reduced rule header as Markdown lines."""
    lines = [
        f"- `{header.name}` ({header.path})",
        f"  description: {header.description}",
        f"  apply: {header.apply}",
    ]
    if header.tags:
        lines.append(f"  tags: {', '.join(header.tags)}")
    # lines.append(f"  visibility: {header.visibility}")
    return lines
