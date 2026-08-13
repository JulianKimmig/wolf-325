"""Behavioral contract tests for the client publication workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).parents[1]
RELEASE_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VALIDATION_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "validate.yml"


def _load_workflow() -> dict[str, Any]:
    """Load the release workflow without YAML 1.1 boolean coercion.

    Returns:
        Parsed workflow mapping whose scalar values remain strings.
    """
    loaded = yaml.load(RELEASE_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(loaded, dict)
    return loaded


def _load_validation_workflow() -> dict[str, Any]:
    """Load the repository-validation workflow as a string-preserving mapping.

    Returns:
        Parsed HACS and hassfest workflow configuration.
    """
    loaded = yaml.load(
        VALIDATION_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert isinstance(loaded, dict)
    return loaded


def test_release_workflow_uses_tag_gated_trusted_publishing() -> None:
    """Require a tag-only, tokenless PyPI publication boundary.

    Returns:
        None.
    """
    workflow = _load_workflow()
    assert workflow["on"] == {"push": {"tags": ["v*"]}}

    publish = workflow["jobs"]["publish"]
    assert publish["environment"] == {
        "name": "pypi",
        "url": "https://pypi.org/p/wolf-325",
    }
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}

    serialized = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in serialized
    assert "UV_PUBLISH_TOKEN" not in serialized


def test_release_workflow_qualifies_artifacts_before_publication() -> None:
    """Require locked tests, tag verification, and build before upload.

    Returns:
        None.
    """
    steps = _load_workflow()["jobs"]["publish"]["steps"]
    commands = [step["run"] for step in steps if "run" in step]

    expected_commands = [
        "uv sync --locked --all-extras --dev",
        'test "${GITHUB_REF_NAME}" = "v$(uv version --short)"',
        "uv run pytest",
        (
            "uv run pytest -c tests/components/wolf_cwl2/pytest.toml "
            "tests/components/wolf_cwl2"
        ),
        "uv build",
        "uv publish --trusted-publishing always",
    ]
    assert commands == expected_commands

    uses = [step["uses"] for step in steps if "uses" in step]
    assert uses[0].startswith("actions/checkout@")
    assert uses[1].startswith("astral-sh/setup-uv@")


def test_repository_validation_uses_hacs_and_hassfest() -> None:
    """Require official HACS and Home Assistant validation on public changes.

    Returns:
        None.
    """
    workflow = _load_validation_workflow()
    assert workflow["on"] == {
        "push": "",
        "pull_request": "",
        "schedule": [{"cron": "0 0 * * *"}],
        "workflow_dispatch": "",
    }
    assert workflow["permissions"] == {}

    hacs_steps = workflow["jobs"]["validate-hacs"]["steps"]
    assert hacs_steps == [
        {
            "name": "HACS validation",
            "uses": "hacs/action@1ebf01c408f29afcb6406bd431bc98fd8cbb15aa",
            "with": {"category": "integration", "comment": "false"},
        }
    ]

    hassfest_steps = workflow["jobs"]["validate-hassfest"]["steps"]
    assert hassfest_steps == [
        {
            "name": "Check out source",
            "uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        },
        {
            "name": "hassfest validation",
            "uses": (
                "home-assistant/actions/hassfest@"
                "a7c616ce81ccda50150bf1595786c71b1883fabb"
            ),
        },
    ]
