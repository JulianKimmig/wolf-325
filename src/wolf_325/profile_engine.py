"""Store-neutral inheritance, validation, capture, and save operations."""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .catalogue import resolve_register_name
from .errors import ProfileError
from .profile_models import ProfileChanges, ResolvedProfile, SavedProfile
from .types import JSONScalar
from .validation import normalize_settings, validate_cross_settings


class ProfileRepository(ABC):
    """Define common profile behavior over an asynchronous document store."""

    VALID_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self) -> None:
        """Initialize repository-level mutation serialization."""
        self._write_lock = asyncio.Lock()

    @abstractmethod
    async def list_profiles(self) -> list[str]:
        """Return available profile identifiers in deterministic order."""

    @abstractmethod
    async def _read_document(self, name: str) -> dict[str, Any]:
        """Read one portable profile document by validated name."""

    @abstractmethod
    async def _write_document(self, name: str, document: Mapping[str, Any]) -> None:
        """Persist one validated portable profile document."""

    @abstractmethod
    async def _exists(self, name: str) -> bool:
        """Return whether one validated profile identifier already exists."""

    def _saved_path(self, name: str) -> Path | None:
        """Return a filesystem path when the repository has one."""
        return None

    async def load(self, name: str) -> ResolvedProfile:
        """Load a profile and all parents into one canonical result.

        Args:
            name: Profile identifier without a JSON suffix.

        Returns:
            Fully resolved profile.
        """
        self._validate_name(name)
        return await self._load_recursive(name, stack=[])

    async def capture_changes(
        self,
        desired: Mapping[str, object],
        *,
        last_profile: str | None,
    ) -> ProfileChanges:
        """Calculate desired ownership changes relative to exact lineage.

        Args:
            desired: Current persistent desired-state ownership.
            last_profile: Exact parent lineage or ``None``.

        Returns:
            Canonical changed settings and inherited releases.
        """
        normalized = normalize_settings(desired, require_restorable=True)
        validate_cross_settings(normalized)
        parent = await self.load(last_profile) if last_profile is not None else None
        inherited = parent.settings if parent is not None else {}
        settings = {
            key: normalized[key]
            for key in sorted(normalized)
            if key not in inherited or inherited[key] != normalized[key]
        }
        unset = tuple(sorted(key for key in inherited if key not in normalized))
        return ProfileChanges(
            extends=last_profile,
            settings=settings,
            unset=unset,
            replace=parent.replace if parent is not None else False,
        )

    async def save_changes(
        self,
        name: str,
        desired: Mapping[str, object],
        *,
        last_profile: str | None,
        description: str = "",
        overwrite: bool = False,
    ) -> SavedProfile:
        """Validate and persist a desired-state delta atomically.

        Args:
            name: New profile identifier without a JSON suffix.
            desired: Current persistent desired-state ownership.
            last_profile: Exact optional lineage parent.
            description: Operator-facing description.
            overwrite: Whether an existing document may be replaced.

        Returns:
            Store-neutral saved profile metadata.
        """
        self._validate_name(name)
        if name.casefold().endswith(".json"):
            raise ProfileError("profile name must be provided without the .json suffix")
        if last_profile == name:
            raise ProfileError(f"profile {name!r} cannot extend itself")
        async with self._write_lock:
            if await self._exists(name) and not overwrite:
                raise ProfileError(f"profile {name!r} already exists")
            changes = await self.capture_changes(desired, last_profile=last_profile)
            if not changes.has_changes:
                raise ProfileError("no desired-state changes to save")
            document = changes.as_document(description)
            await self._validate_candidate_graph(name, document)
            await self._write_document(name, document)
        return SavedProfile(name, self._saved_path(name), description, changes)

    async def _validate_candidate_graph(
        self, name: str, document: Mapping[str, Any]
    ) -> None:
        """Validate the complete catalogue after adding or replacing a document."""
        names = set(await self.list_profiles())
        names.add(name)
        documents: dict[str, dict[str, Any]] = {}
        for profile_name in names:
            documents[profile_name] = (
                dict(document)
                if profile_name == name
                else await self._read_document(profile_name)
            )

        async def read(candidate: str) -> dict[str, Any]:
            """Read one candidate graph document from memory."""
            try:
                return documents[candidate]
            except KeyError as exc:
                raise ProfileError(f"profile {candidate!r} does not exist") from exc

        for profile_name in sorted(documents):
            await self._resolve(profile_name, [], read)

    async def _load_recursive(
        self, name: str, stack: list[str]
    ) -> ResolvedProfile:
        """Resolve one stored profile while tracking inheritance cycles."""
        return await self._resolve(name, stack, self._read_document)

    async def _resolve(self, name: str, stack: list[str], reader: Any) -> ResolvedProfile:
        """Resolve one document using an asynchronous document reader."""
        self._validate_name(name)
        if name in stack:
            raise ProfileError(f"profile inheritance cycle: {' -> '.join([*stack, name])}")
        document = await reader(name)
        extends_raw = document.get("extends", [])
        if isinstance(extends_raw, str):
            extends = [extends_raw]
        elif isinstance(extends_raw, list) and all(
            isinstance(item, str) for item in extends_raw
        ):
            extends = list(extends_raw)
        else:
            raise ProfileError(f"{name}: extends must be a string or list of strings")
        settings_raw = document.get("settings", {})
        if not isinstance(settings_raw, Mapping):
            raise ProfileError(f"{name}: settings must be an object")
        unset_raw = document.get("unset", [])
        if not isinstance(unset_raw, list) or not all(
            isinstance(item, str) for item in unset_raw
        ):
            raise ProfileError(f"{name}: unset must be a list of setting names")
        settings: dict[str, JSONScalar] = {}
        unset: list[str] = []
        sources: list[str] = []
        for parent_name in extends:
            parent = await self._resolve(parent_name, [*stack, name], reader)
            settings.update(parent.settings)
            for key in parent.unset:
                settings.pop(key, None)
                if key not in unset:
                    unset.append(key)
            sources.extend(parent.sources)
        for key in (resolve_register_name(item) for item in unset_raw):
            settings.pop(key, None)
            if key not in unset:
                unset.append(key)
        own = normalize_settings(settings_raw, require_restorable=True)
        for key in own:
            if key in unset:
                unset.remove(key)
        settings.update(own)
        validate_cross_settings(settings)
        return ResolvedProfile(
            name=name,
            description=str(document.get("description", "")),
            settings=settings,
            unset=unset,
            replace=bool(document.get("replace", False)),
            sources=[*dict.fromkeys([*sources, name])],
        )

    @classmethod
    def _validate_name(cls, name: str) -> None:
        """Reject unsafe or unsupported profile identifiers."""
        if not cls.VALID_NAME.fullmatch(name):
            raise ProfileError(f"invalid profile name {name!r}")
