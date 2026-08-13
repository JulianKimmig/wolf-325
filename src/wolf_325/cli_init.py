"""Creation of initial controller configuration and example profiles."""

from __future__ import annotations

from pathlib import Path
import copy

from .config import DEFAULT_CONFIG, atomic_json_write
from .example_profiles import example_profile_documents
from .errors import ConfigError


async def initialize_config(
    config_path: Path, host: str, force: bool
) -> None:
    """Create a complete config and example profiles without unsafe overwrite."""
    if config_path.exists() and not force:
        raise ConfigError(f"{config_path} already exists; use --force to overwrite")
    payload = copy.deepcopy(DEFAULT_CONFIG)
    payload["connection"]["host"] = host
    await atomic_json_write(config_path, payload)
    profiles = config_path.parent / str(payload["profiles_dir"])
    profiles.mkdir(parents=True, exist_ok=True)
    for name, document in example_profile_documents().items():
        target = profiles / f"{name}.json"
        if not target.exists() or force:
            await atomic_json_write(target, document)
    print(f"created {config_path}")
    print(f"created example profiles in {profiles}")
