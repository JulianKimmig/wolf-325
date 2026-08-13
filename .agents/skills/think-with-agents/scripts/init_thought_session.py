#!/usr/bin/env python3
import argparse
import re
from datetime import datetime
from pathlib import Path


SAFE_TITLE_FALLBACK = "task"


def slugify_title(title):
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or SAFE_TITLE_FALLBACK


def _template(title, purpose):
    return f"""# {title}

Purpose: {purpose}

## Source Task

Append the original task or relevant task excerpt here.

## Chain-of-Thought Summary

Record safe, reusable reasoning notes here: rationale summaries, assumptions, explored alternatives, tradeoffs, temporary hypotheses, discarded paths, and decision reasons. Do not include private hidden deliberation verbatim.

## Findings

Append concrete findings, open questions, contradictions, risks, and useful observations here.

## Running Log

- Session file created.
"""


def create_session(base_dir, title, timestamp=None):
    thoughts_dir = Path(base_dir) / ".thoughts"
    thoughts_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify_title(title)
    session_dir = thoughts_dir / slug
    if session_dir.exists():
        suffix = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
        session_dir = thoughts_dir / f"{slug}-{suffix}"

    session_dir.mkdir(parents=False, exist_ok=False)
    (session_dir / "results").mkdir()

    files = {
        "perspectives.md": "Perspective exploration before solving.",
        "clarification.md": "Clarification questions, user answers, and resolved assumptions.",
        "summary.md": "Final synthesis across perspectives, clarifications, and agent results.",
    }
    for filename, purpose in files.items():
        (session_dir / filename).write_text(
            _template(title=title, purpose=purpose),
            encoding="utf-8",
        )

    return session_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create a .thoughts task workspace for think-with-agents."
    )
    parser.add_argument("title", help="Human-readable task title")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory where .thoughts should be created",
    )
    args = parser.parse_args()

    session_dir = create_session(Path(args.base_dir), args.title)
    print(session_dir)


if __name__ == "__main__":
    main()
