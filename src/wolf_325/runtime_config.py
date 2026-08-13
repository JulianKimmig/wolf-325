"""Host-neutral runtime configuration and desired-state persistence contracts."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .catalogue import resolve_register_name
from .config import DEFAULT_CONFIG, deep_merge, validate_config
from .errors import ConfigError
from .types import JSONScalar
from .validation import normalize_settings, validate_cross_settings

ConfigSaveCallback = Callable[[dict[str, Any]], Awaitable[None]]


class ConfigRepository(Protocol):
    """Describe configuration behavior required by the public controller."""

    @property
    def data(self) -> dict[str, Any]:
        """Return an isolated loaded configuration."""

    async def load(self) -> dict[str, Any]:
        """Load and validate configuration state."""

    async def save(self) -> None:
        """Persist current configuration state."""

    async def update_desired(
        self,
        patch: Mapping[str, JSONScalar] | None = None,
        *,
        unset: Sequence[str] = (),
        replace: bool = False,
        last_profile: str | None = None,
    ) -> dict[str, JSONScalar]:
        """Atomically mutate desired ownership and lineage."""

    def resolve_relative_path(self, configured: str | None) -> Path | None:
        """Resolve an optional host-owned path or return ``None``."""


class RuntimeConfigStore:
    """Store normalized controller configuration in a host-owned repository."""

    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        save_callback: ConfigSaveCallback | None = None,
    ) -> None:
        """Initialize an isolated runtime configuration.

        Args:
            config: Partial or complete schema-versioned controller settings.
            save_callback: Awaited callback for durable host persistence.
        """
        self._supplied = copy.deepcopy(dict(config))
        self._save_callback = save_callback
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    @property
    def data(self) -> dict[str, Any]:
        """Return loaded state or fail before :meth:`load`."""
        if self._data is None:
            raise ConfigError("configuration has not been loaded")
        return copy.deepcopy(self._data)

    async def load(self) -> dict[str, Any]:
        """Merge defaults, validate, and canonicalize runtime configuration."""
        async with self._lock:
            merged = deep_merge(DEFAULT_CONFIG, self._supplied)
            validate_config(merged)
            merged["desired"] = normalize_settings(
                merged.get("desired", {}), require_restorable=True
            )
            self._data = merged
            return copy.deepcopy(merged)

    async def save(self) -> None:
        """Await host persistence for the current loaded state."""
        async with self._lock:
            data = self._require_data()
            if self._save_callback is not None:
                await self._save_callback(copy.deepcopy(data))

    async def update_desired(
        self,
        patch: Mapping[str, JSONScalar] | None = None,
        *,
        unset: Sequence[str] = (),
        replace: bool = False,
        last_profile: str | None = None,
    ) -> dict[str, JSONScalar]:
        """Commit desired ownership and lineage before exposing the mutation."""
        async with self._lock:
            data = self._require_data()
            desired: dict[str, JSONScalar] = (
                {} if replace else dict(data.get("desired", {}))
            )
            for name in unset:
                desired.pop(resolve_register_name(name), None)
            if patch:
                desired.update(patch)
            validate_cross_settings(desired)
            candidate = copy.deepcopy(data)
            candidate["desired"] = desired
            candidate["last_profile"] = last_profile
            if self._save_callback is not None:
                await self._save_callback(copy.deepcopy(candidate))
            self._data = candidate
            return copy.deepcopy(desired)

    def resolve_relative_path(self, configured: str | None) -> None:
        """Disable client-owned file paths for a host-managed runtime."""
        return None

    def _require_data(self) -> dict[str, Any]:
        """Return mutable loaded data or raise a domain configuration error."""
        if self._data is None:
            raise ConfigError("configuration has not been loaded")
        return self._data
