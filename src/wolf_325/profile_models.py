"""Public profile data models shared by filesystem and host repositories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .types import JSONScalar


@dataclass(slots=True)
class ResolvedProfile:
    """Represent a fully inherited and canonicalized named profile.

    Attributes:
        name: Canonical profile identifier.
        description: Operator-facing description.
        settings: Fully resolved persistent setting values.
        unset: Canonical inherited keys released by the profile.
        replace: Whether application replaces prior desired ownership.
        sources: Ordered unique inheritance sources.
    """

    name: str
    description: str
    settings: dict[str, JSONScalar]
    unset: list[str]
    replace: bool
    sources: list[str]


@dataclass(frozen=True, slots=True)
class ProfileChanges:
    """Represent a desired-state delta relative to an optional parent profile."""

    extends: str | None
    settings: dict[str, JSONScalar]
    unset: tuple[str, ...]
    replace: bool

    @property
    def has_changes(self) -> bool:
        """Return whether the delta contains a setting override or release."""
        return bool(self.settings or self.unset)

    def as_document(self, description: str) -> dict[str, object]:
        """Build the stable portable document for this delta.

        Args:
            description: Operator-provided profile description.

        Returns:
            JSON-compatible profile document with optional inheritance.
        """
        document: dict[str, object] = {
            "description": description,
            "replace": self.replace,
            "settings": dict(self.settings),
            "unset": list(self.unset),
        }
        if self.extends is not None:
            document["extends"] = self.extends
        return document


@dataclass(frozen=True, slots=True)
class SavedProfile:
    """Describe a successfully persisted profile independent of storage host."""

    name: str
    path: Path | None
    description: str
    changes: ProfileChanges
