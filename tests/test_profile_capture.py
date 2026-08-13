"""Behavior tests for saving desired-state deltas as composable profiles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wolf_325.errors import ProfileError
from wolf_325.controller import WolfCWL2
from wolf_325.profiles import ProfileLoader


async def test_capture_diffs_desired_state_against_resolved_parent(
    tmp_path: Path,
) -> None:
    """A derived profile stores only changed/new settings and removed parent keys."""
    (tmp_path / "base.json").write_text(
        json.dumps(
            {
                "replace": True,
                "settings": {
                    "remote_control_mode": "level",
                    "remote_ventilation_level": "normal",
                    "bypass_mode": "automatic",
                },
            }
        ),
        encoding="utf-8",
    )
    loader = ProfileLoader(tmp_path)
    desired = {
        "remote_control_mode": "level",
        "remote_ventilation_level": "high",
        "filter_warning_days": 90,
    }

    changes = await loader.capture_changes(desired, last_profile="base")

    assert changes.extends == "base"
    assert changes.settings == {
        "filter_warning_days": 90,
        "remote_ventilation_level": "high",
    }
    assert changes.unset == ("bypass_mode",)
    assert changes.replace is True


async def test_saved_child_loads_to_the_captured_desired_state(tmp_path: Path) -> None:
    """The emitted extends/settings/unset document resolves back to desired state."""
    (tmp_path / "base.json").write_text(
        json.dumps(
            {
                "settings": {
                    "remote_control_mode": "level",
                    "remote_ventilation_level": "normal",
                    "bypass_mode": "automatic",
                }
            }
        ),
        encoding="utf-8",
    )
    desired = {
        "remote_control_mode": "level",
        "remote_ventilation_level": "low",
        "filter_warning_days": 120,
    }
    loader = ProfileLoader(tmp_path)

    saved = await loader.save_changes(
        "quiet-custom",
        desired,
        last_profile="base",
        description="Quiet profile with a longer filter interval",
    )

    document = json.loads((tmp_path / "quiet-custom.json").read_text(encoding="utf-8"))
    assert document == {
        "description": "Quiet profile with a longer filter interval",
        "extends": "base",
        "replace": False,
        "settings": {
            "filter_warning_days": 120,
            "remote_ventilation_level": "low",
        },
        "unset": ["bypass_mode"],
    }
    assert saved.name == "quiet-custom"
    assert saved.path == tmp_path / "quiet-custom.json"
    resolved = await loader.load("quiet-custom")
    assert resolved.settings == desired


async def test_standalone_capture_stores_complete_desired_state(
    tmp_path: Path,
) -> None:
    """Without a loaded parent, every desired setting is saved and extends is absent."""
    loader = ProfileLoader(tmp_path)
    desired = {
        "remote_control_mode": "airflow",
        "remote_airflow_m3h": 170,
    }

    saved = await loader.save_changes(
        "standalone", desired, last_profile=None, description="Direct airflow"
    )

    assert saved.changes.extends is None
    document = json.loads((tmp_path / "standalone.json").read_text(encoding="utf-8"))
    assert "extends" not in document
    assert document["settings"] == desired
    assert document["unset"] == []


@pytest.mark.parametrize(
    ("name", "last_profile", "message"),
    [
        ("../escape", None, "invalid profile name"),
        ("named.json", None, "without the .json suffix"),
        ("base", "base", "cannot extend itself"),
        ("child", "missing", "does not exist"),
    ],
)
async def test_capture_rejects_invalid_names_and_parent_relationships(
    tmp_path: Path, name: str, last_profile: str | None, message: str
) -> None:
    """Profile paths and inheritance remain valid before any file is created."""
    if last_profile == "base":
        (tmp_path / "base.json").write_text(
            json.dumps({"settings": {"remote_standby": False}}),
            encoding="utf-8",
        )
    loader = ProfileLoader(tmp_path)

    with pytest.raises(ProfileError, match=message):
        await loader.save_changes(
            name,
            {"remote_standby": True},
            last_profile=last_profile,
        )


async def test_capture_rejects_empty_delta_and_requires_explicit_overwrite(
    tmp_path: Path,
) -> None:
    """Empty or colliding captures fail without altering existing profile files."""
    (tmp_path / "base.json").write_text(
        json.dumps({"settings": {"remote_standby": False}}),
        encoding="utf-8",
    )
    existing = tmp_path / "child.json"
    existing.write_text(json.dumps({"description": "keep"}), encoding="utf-8")
    loader = ProfileLoader(tmp_path)

    with pytest.raises(ProfileError, match="no desired-state changes"):
        await loader.save_changes(
            "empty",
            {"remote_standby": False},
            last_profile="base",
        )
    with pytest.raises(ProfileError, match="already exists"):
        await loader.save_changes(
            "child",
            {"remote_standby": True},
            last_profile="base",
        )
    assert json.loads(existing.read_text(encoding="utf-8")) == {
        "description": "keep"
    }

    await loader.save_changes(
        "child",
        {"remote_standby": True},
        last_profile="base",
        overwrite=True,
    )
    assert json.loads(existing.read_text(encoding="utf-8"))["extends"] == "base"


async def test_persistent_edits_preserve_loaded_profile_as_capture_parent(
    controller: tuple[WolfCWL2, object], config_path: Path
) -> None:
    """Normal persistent writes retain the loaded base used by a later capture."""
    (config_path.parent / "profiles" / "base.json").write_text(
        json.dumps({"settings": {"remote_airflow_m3h": 100}}),
        encoding="utf-8",
    )
    instance, _ = controller
    await instance.start(restore=False, background=False)
    await instance.apply_profile("base", persist=True)

    await instance.set_setting("remote_airflow_m3h", 170, persist=True)

    assert instance.config["last_profile"] == "base"
    saved = await instance.save_profile("derived")
    assert saved.changes.extends == "base"
    assert saved.changes.settings == {"remote_airflow_m3h": 170}


async def test_persistent_release_is_saved_as_parent_unset(
    controller: tuple[WolfCWL2, object], config_path: Path
) -> None:
    """Releasing an inherited desired key retains lineage and emits child unset."""
    (config_path.parent / "profiles" / "base.json").write_text(
        json.dumps(
            {
                "settings": {
                    "remote_airflow_m3h": 100,
                    "remote_standby": False,
                }
            }
        ),
        encoding="utf-8",
    )
    instance, _ = controller
    await instance.start(restore=False, background=False)
    await instance.apply_profile("base", persist=True)

    await instance.set_settings({}, persist=True, unset=("remote_standby",))

    assert instance.config["last_profile"] == "base"
    saved = await instance.save_profile("without-standby")
    assert saved.changes.extends == "base"
    assert saved.changes.settings == {}
    assert saved.changes.unset == ("remote_standby",)
