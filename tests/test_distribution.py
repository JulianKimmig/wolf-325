"""Behavioral tests for locally built client distribution artifacts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tarfile
import zipfile


REPOSITORY_ROOT = Path(__file__).parents[1]


def test_sdist_contains_only_rebuildable_client_source(tmp_path: Path) -> None:
    """Build an sdist and reject repository caches or host-adapter sources.

    Args:
        tmp_path: Isolated pytest directory that receives the generated sdist.

    Returns:
        None.
    """
    environment = os.environ.copy()
    environment["UV_CACHE_DIR"] = str(REPOSITORY_ROOT / ".cache" / "uv")
    completed = subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(tmp_path)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr

    archives = list(tmp_path.glob("wolf_325-*.tar.gz"))
    assert len(archives) == 1
    archive = archives[0]
    with tarfile.open(archive, "r:gz") as source_distribution:
        members = source_distribution.getnames()

    assert any(name.endswith("/pyproject.toml") for name in members)
    assert any(name.endswith("/README.md") for name in members)
    assert any(name.endswith("/LICENSE") for name in members)
    assert any(name.endswith("/src/wolf_325/__init__.py") for name in members)
    forbidden_parts = {".cache", ".venv", ".venv-wsl", "custom_components"}
    assert not any(forbidden_parts.intersection(Path(name).parts) for name in members)
    assert archive.stat().st_size < 5_000_000


def test_wheel_declares_and_contains_mit_license(tmp_path: Path) -> None:
    """Build a wheel whose metadata and included notice agree on MIT.

    Args:
        tmp_path: Isolated pytest directory that receives the generated wheel.

    Returns:
        None.
    """
    environment = os.environ.copy()
    environment["UV_CACHE_DIR"] = str(REPOSITORY_ROOT / ".cache" / "uv")
    completed = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr

    wheels = list(tmp_path.glob("wolf_325-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        metadata_name = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        license_name = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/licenses/LICENSE")
        )
        metadata = wheel.read(metadata_name).decode("utf-8")
        license_text = wheel.read(license_name).decode("utf-8")

    assert "License-Expression: MIT\n" in metadata
    assert "License-File: LICENSE\n" in metadata
    assert "Author: Julian Kimmig\n" in metadata
    assert (
        "Project-URL: Repository, https://github.com/JulianKimmig/wolf-325\n"
        in metadata
    )
    assert (
        "Project-URL: Documentation, "
        "https://github.com/JulianKimmig/wolf-325#readme\n" in metadata
    )
    assert (
        "Project-URL: Issues, https://github.com/JulianKimmig/wolf-325/issues\n"
        in metadata
    )
    assert "Copyright (c) 2026 Julian Kimmig" in license_text
    assert "Permission is hereby granted, free of charge" in license_text
