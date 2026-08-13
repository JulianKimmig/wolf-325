"""Behavioral contracts for continuous integration and dependency updates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).parents[1]
DEPENDABOT_CONFIG = REPOSITORY_ROOT / ".github" / "dependabot.yml"
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML without coercing GitHub's ``on`` key to a boolean.

    Args:
        path: Repository YAML file to parse.

    Returns:
        Parsed top-level mapping whose scalar values remain strings.
    """
    loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(loaded, dict)
    return loaded


def test_dependabot_tracks_actions_and_uv_lockfile() -> None:
    """Require update sources that exist in this uv-managed repository.

    Returns:
        None.
    """
    config = _load_yaml(DEPENDABOT_CONFIG)
    assert config == {
        "version": "2",
        "updates": [
            {
                "package-ecosystem": "github-actions",
                "directory": "/",
                "schedule": {"interval": "weekly"},
            },
            {
                "package-ecosystem": "uv",
                "directory": "/",
                "schedule": {"interval": "weekly"},
            },
        ],
    }


def test_ci_uses_locked_repository_native_commands() -> None:
    """Require CI to qualify the client, integration, and distributions.

    Returns:
        None.
    """
    workflow = _load_yaml(CI_WORKFLOW)
    assert workflow["on"] == {
        "push": {"branches": ["main"]},
        "pull_request": "",
        "workflow_dispatch": "",
    }
    assert workflow["permissions"] == {"contents": "read"}

    steps = workflow["jobs"]["test"]["steps"]
    uses = [step["uses"] for step in steps if "uses" in step]
    assert uses == [
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b",
    ]
    commands = [step["run"] for step in steps if "run" in step]
    assert commands == [
        "uv sync --locked --all-extras --dev",
        "uv run pytest",
        (
            "uv run pytest -c tests/components/wolf_cwl2/pytest.toml "
            "tests/components/wolf_cwl2"
        ),
        "uv build",
    ]

    serialized = CI_WORKFLOW.read_text(encoding="utf-8")
    for foreign_reference in (
        "requirements_test.txt",
        "hacs_wab11",
        "python -m pip",
        "ruff ",
        "mypy ",
    ):
        assert foreign_reference not in serialized

    assert not (REPOSITORY_ROOT / "requirements_dev.txt").exists()
    assert not (REPOSITORY_ROOT / "requirements_test.txt").exists()
