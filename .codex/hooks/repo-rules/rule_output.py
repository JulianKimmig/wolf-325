"""Output formatting for the repo rule bootstrap hook."""

from __future__ import annotations

from rule_metadata import RuleHeader, SkippedRule


def format_bootstrap_context(
    headers: list[RuleHeader],
    skipped: list[SkippedRule],
) -> str:
    """Format bounded startup context for Codex hooks.

    Args:
        headers: All parseable rule headers.
        skipped: Malformed rule diagnostics.

    Returns:
        Markdown additional context for the hook response.
    """
    always_headers = [header for header in headers if header.visibility == "always"]
    lines = [
        "## Local Rule Bootstrap",
        "",
        "Repo rules are retrieved on demand. Before code edits, config or hook",
        "changes, generated-file updates, long-running commands, external tool",
        "use, or subagent delegation, query local rules with:",
        "",
        "`python .agents/skills/repo-rule-search/scripts/query_rules.py --tags \"<expr>\"`",
        "",
        "Use Boolean tags with `AND`, `OR`, `NOT`, and parentheses.",
        "If possible spawn a subagent to retrieve the relevant rules for you (unless you are this agent)."
        "Read the full rule file for any returned rule that applies or remains uncertain.",
        "",
    ]
    if skipped:
        lines.extend(["Skipped malformed rule files:", ""])
        for skipped_rule in skipped:
            lines.append(f"- `{skipped_rule.path}`: {skipped_rule.reason}")
        lines.append("")
    if not always_headers:
        lines.append("No always-visible local rules are currently defined.")
        return "\n".join(lines) + "\n"
    lines.extend(["Always-visible local rules:", ""])
    for header in always_headers:
        lines.extend(_format_header_lines(header))
    return "\n".join(lines) + "\n"


def _format_header_lines(header: RuleHeader) -> list[str]:
    """Format one reduced rule header as Markdown lines."""
    lines = [
        f"- `{header.name}` ({header.path})",
        f"  description: {header.description}",
        f"  apply: {header.apply}",
    ]
    # if header.tags:
    #     lines.append(f"  tags: {', '.join(header.tags)}")
    # lines.append(f"  visibility: {header.visibility}")
    return lines
