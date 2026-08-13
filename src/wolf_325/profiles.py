"""Filesystem and in-memory repositories for composable profiles."""

from __future__ import annotations

import copy
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from .async_utils import run_in_worker
from .config import atomic_json_write, read_json
from .errors import ProfileError
from .profile_engine import ProfileRepository
from .profile_models import ProfileChanges, ResolvedProfile, SavedProfile

ProfileSaveCallback = Callable[[dict[str, dict[str, Any]]], Awaitable[None]]


class ProfileLoader(ProfileRepository):
    """Persist recursively composable profiles in one filesystem directory."""

    def __init__(self, directory: Path) -> None:
        """Initialize a loader rooted at the configured profile directory.

        Args:
            directory: Directory containing portable JSON profile documents.
        """
        super().__init__()
        self.directory = directory

    async def list_profiles(self) -> list[str]:
        """List JSON profile stems without blocking the event loop."""
        def discover() -> list[str]:
            """Discover profile paths on a worker thread."""
            if not self.directory.exists():
                return []
            return sorted(
                path.stem for path in self.directory.glob("*.json") if path.is_file()
            )

        return await run_in_worker(discover)

    async def _read_document(self, name: str) -> dict[str, Any]:
        """Read one validated profile document from the repository directory."""
        path = self._profile_path(name)
        if not await run_in_worker(path.exists):
            raise ProfileError(f"profile {name!r} does not exist in {self.directory}")
        return await read_json(path)

    async def _write_document(self, name: str, document: Mapping[str, Any]) -> None:
        """Atomically write one validated profile document."""
        await atomic_json_write(self._profile_path(name), document)

    async def _exists(self, name: str) -> bool:
        """Return whether a profile path exists without blocking the event loop."""
        return await run_in_worker(self._profile_path(name).exists)

    def _saved_path(self, name: str) -> Path:
        """Return the concrete path persisted for a profile."""
        return self._profile_path(name)

    def _profile_path(self, name: str) -> Path:
        """Resolve a validated profile path and reject directory escape."""
        path = (self.directory / f"{name}.json").resolve()
        try:
            path.relative_to(self.directory.resolve())
        except ValueError as exc:
            raise ProfileError("profile path escapes profiles_dir") from exc
        return path


class MemoryProfileRepository(ProfileRepository):
    """Persist portable profiles in host-owned memory with an async save hook."""

    def __init__(
        self,
        documents: Mapping[str, Mapping[str, Any]] | None = None,
        *,
        save_callback: ProfileSaveCallback | None = None,
    ) -> None:
        """Initialize an isolated portable document catalogue.

        Args:
            documents: Initial profile documents keyed by profile identifier.
            save_callback: Awaited host persistence callback after mutations.
        """
        super().__init__()
        self._documents = copy.deepcopy(dict(documents or {}))
        self._save_callback = save_callback

    async def list_profiles(self) -> list[str]:
        """Return deterministic in-memory profile identifiers."""
        return sorted(self._documents)

    async def _read_document(self, name: str) -> dict[str, Any]:
        """Return an isolated in-memory profile document."""
        try:
            return copy.deepcopy(self._documents[name])
        except KeyError as exc:
            raise ProfileError(f"profile {name!r} does not exist") from exc

    async def _write_document(self, name: str, document: Mapping[str, Any]) -> None:
        """Commit a profile document and await host persistence."""
        candidate = copy.deepcopy(self._documents)
        candidate[name] = copy.deepcopy(dict(document))
        if self._save_callback is not None:
            await self._save_callback(copy.deepcopy(candidate))
        self._documents = candidate

    async def _exists(self, name: str) -> bool:
        """Return whether the in-memory catalogue contains a profile."""
        return name in self._documents


__all__ = [
    "MemoryProfileRepository",
    "ProfileChanges",
    "ProfileLoader",
    "ProfileRepository",
    "ResolvedProfile",
    "SavedProfile",
]
