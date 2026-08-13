"""Parse Markdown rule frontmatter for the repo rule bootstrap hook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SKIPPED_FILENAMES = {"overview.md", "index.md", "readme.md"}
REQUIRED_FIELDS = ("name", "description", "apply")
VISIBILITY_ALWAYS = "always"
VISIBILITY_ON_REQUEST = "on_request"
VISIBILITY_NEVER = "never"
VISIBILITY_VALUES = {
    "always": VISIBILITY_ALWAYS,
    "on request": VISIBILITY_ON_REQUEST,
    "on_request": VISIBILITY_ON_REQUEST,
    "indexed": VISIBILITY_ON_REQUEST,
    "never": VISIBILITY_NEVER,
    "manual": VISIBILITY_NEVER,
    "manual_only": VISIBILITY_NEVER,
    "manual only": VISIBILITY_NEVER,
}


@dataclass(frozen=True)
class RuleHeader:
    """Rule metadata used for reduced prompt context.

    Args:
        name: Stable human-facing rule name.
        description: Short rule summary.
        apply: Human-readable condition for applying the rule.
        path: Repository-relative rule file path.
        tags: Normalized tag tuple used by query filtering.
        visibility: Normalized visibility behavior.
    """

    name: str
    description: str
    apply: str
    path: str
    tags: tuple[str, ...] = ()
    visibility: str = VISIBILITY_ON_REQUEST


@dataclass(frozen=True)
class SkippedRule:
    """Skipped rule diagnostic.

    Args:
        path: Display path for the skipped rule.
        reason: Parse or validation failure reason.
    """

    path: str
    reason: str


def load_rule_headers(root: Path | None) -> tuple[list[RuleHeader], list[SkippedRule]]:
    """Load parseable rule headers and collect skipped-rule diagnostics.

    Args:
        root: Repository root containing ``.rules``.

    Returns:
        Parsed rule headers and diagnostics for skipped rules.
    """
    if root is None:
        return [], [SkippedRule(".rules", "no .rules directory found")]
    headers: list[RuleHeader] = []
    skipped: list[SkippedRule] = []
    for path in _iter_rule_files(root):
        try:
            headers.append(parse_rule_header(path, root))
        except ValueError as exc:
            display_path = _display_path(path, root)
            reason = str(exc).replace(str(path), display_path)
            skipped.append(SkippedRule(display_path, reason))
    return headers, skipped


def parse_rule_header(path: Path, root: Path) -> RuleHeader:
    """Parse one rule frontmatter header.

    Args:
        path: Markdown rule file to parse.
        root: Repository root used for relative path output.

    Returns:
        Parsed rule header metadata.
    """
    fields = _read_frontmatter(path)
    missing = [field for field in REQUIRED_FIELDS if not fields.get(field)]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{path} is missing required header field(s): {joined}")
    return RuleHeader(
        name=fields["name"],
        description=fields["description"],
        apply=fields["apply"],
        path=path.relative_to(root).as_posix(),
        tags=_parse_tags(fields.get("tags", "")),
        visibility=_parse_visibility(fields.get("visibility", "")),
    )


def find_rules_root(cwd: Path) -> Path | None:
    """Find the nearest ancestor that owns a ``.rules`` directory.

    Args:
        cwd: Starting directory for the search.

    Returns:
        Directory containing ``.rules``, or ``None`` when not found.
    """
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".rules").is_dir():
            return candidate
    return None


def visible_in_query(header: RuleHeader, *, include_manual: bool) -> bool:
    """Return whether a header can be returned by query mode.

    Args:
        header: Rule header to evaluate.
        include_manual: Whether manual-only rules are allowed.

    Returns:
        True when the header is discoverable for this query.
    """
    if header.visibility == VISIBILITY_NEVER:
        return include_manual
    return True


def _iter_rule_files(root: Path) -> list[Path]:
    """List Markdown rule files under ``.rules`` recursively.

    Args:
        root: Repository root containing ``.rules``.

    Returns:
        Sorted rule file paths, excluding index files.
    """
    rules_dir = root / ".rules"
    if not rules_dir.is_dir():
        return []
    return sorted(
        path
        for path in rules_dir.rglob("*.md")
        if path.is_file() and path.name.lower() not in SKIPPED_FILENAMES
    )


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Read simple ``key: value`` frontmatter from a Markdown file.

    Args:
        path: Markdown file to inspect.

    Returns:
        Parsed frontmatter fields.
    """
    with path.open(encoding="utf-8") as handle:
        first_line = handle.readline()
        if first_line.rstrip("\n") != "---":
            raise ValueError(f"{path} must start with a frontmatter delimiter")
        header_lines: list[str] = []
        for line in handle:
            if line.rstrip("\n") == "---":
                return _parse_header_lines(path, header_lines)
            header_lines.append(line.rstrip("\n"))
    raise ValueError(f"{path} is missing the closing frontmatter delimiter")


def _parse_header_lines(path: Path, lines: list[str]) -> dict[str, str]:
    """Parse simple frontmatter lines into fields.

    Args:
        path: Source path used in validation errors.
        lines: Header lines between frontmatter delimiters.

    Returns:
        Mapping of parsed header keys to values.
    """
    fields: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip():
            raise ValueError(f"{path} has invalid header line: {line}")
        fields[key.strip()] = value.strip()
    return fields


def _parse_tags(raw_tags: str) -> tuple[str, ...]:
    """Parse comma-separated tags into normalized unique tags.

    Args:
        raw_tags: Raw ``tags`` frontmatter value.

    Returns:
        Sorted normalized tag tuple.
    """
    tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in raw_tags.split(","):
        tag = raw_tag.strip().lower()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tuple(tags)


def _parse_visibility(raw_visibility: str) -> str:
    """Parse a visibility value into its normalized representation.

    Args:
        raw_visibility: Raw ``visibility`` frontmatter value.

    Returns:
        Normalized visibility value.
    """
    if not raw_visibility.strip():
        return VISIBILITY_ON_REQUEST
    key = raw_visibility.strip().lower().replace("-", "_")
    visibility = VISIBILITY_VALUES.get(key)
    if visibility is None:
        expected = ", ".join(sorted(VISIBILITY_VALUES))
        raise ValueError(f"visibility must be one of: {expected}")
    return visibility


def _display_path(path: Path, root: Path) -> str:
    """Return a readable path for diagnostics.

    Args:
        path: Rule file path.
        root: Repository root used for relative output.

    Returns:
        Path relative to ``root`` when possible.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
