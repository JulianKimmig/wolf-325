"""Behavioral contract tests for the client publication workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).parents[1]
RELEASE_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VALIDATION_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "validate.yml"
HACS_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "hacs.yaml"
HASSFEST_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "hassfest.yaml"


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
        (
            "uv run --isolated --all-extras --with pymodbus==3.11.2 pytest "
            "tests/test_transport.py tests/test_transport_polling.py "
            "tests/test_controller.py tests/test_runtime_edges.py "
            "tests/test_setting_relations.py"
        ),
        (
            "uv run --isolated --all-extras --with pymodbus==3.13.1 pytest "
            "tests/test_transport.py tests/test_transport_polling.py "
            "tests/test_controller.py tests/test_runtime_edges.py "
            "tests/test_setting_relations.py"
        ),
        "uv build",
        "uv publish --trusted-publishing always",
    ]
    assert commands == expected_commands

    uses = [step["uses"] for step in steps if "uses" in step]
    assert [reference.split("@", 1)[0] for reference in uses] == [
        "actions/checkout",
        "astral-sh/setup-uv",
    ]


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

    assert workflow["jobs"] == {
        "validate-hacs": {
            "name": "HACS",
            "uses": "./.github/workflows/hacs.yaml",
        },
        "validate-hassfest": {
            "name": "hassfest",
            "uses": "./.github/workflows/hassfest.yaml",
        },
    }

    hacs = yaml.load(
        HACS_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert hacs["on"] == {"workflow_call": ""}
    assert hacs["permissions"] == {}
    hacs_steps = hacs["jobs"]["validate"]["steps"]
    assert len(hacs_steps) == 1
    assert hacs_steps[0]["name"] == "HACS validation"
    assert hacs_steps[0]["uses"].split("@", 1)[0] == "hacs/action"
    assert hacs_steps[0]["with"] == {
        "category": "integration",
        "comment": "false",
    }

    hassfest = yaml.load(
        HASSFEST_WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert hassfest["on"] == {"workflow_call": ""}
    assert hassfest["permissions"] == {}
    hassfest_steps = hassfest["jobs"]["validate"]["steps"]
    assert [step["name"] for step in hassfest_steps] == [
        "Check out source",
        "hassfest validation",
    ]
    assert [step["uses"].split("@", 1)[0] for step in hassfest_steps] == [
        "actions/checkout",
        "home-assistant/actions/hassfest",
    ]
