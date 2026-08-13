"""Durable, versioned Home Assistant Store ownership for one config entry."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from homeassistant.core import HomeAssistant
from wolf_325 import MemoryProfileRepository, ProfileRepository, normalize_settings

from .const import DOMAIN
from .storage_backend import MigratingEntryDataStore
from .storage_errors import EntryStoreError
from .storage_models import (
    StorePayloadError,
    UnsupportedStoreSchemaError,
    new_store_payload,
    validate_store_payload,
)
from .storage_profiles import build_profile_repository, validate_profile_repository

STORE_KEY_PREFIX: Final = f"{DOMAIN}."


class EntryStore:
    """Own one config entry's desired, lineage, and profile transaction state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize an unloaded private Store owner.

        Args:
            hass: Home Assistant instance providing Store persistence.
            entry_id: Immutable Home Assistant config-entry identifier.
        """
        self.hass = hass
        self.storage_key = f"{STORE_KEY_PREFIX}{entry_id}"
        self._store = MigratingEntryDataStore(hass, self.storage_key)
        self._lock = asyncio.Lock()
        self._payload: dict[str, Any] | None = None
        self._profile_repository: MemoryProfileRepository | None = None

    @property
    def path(self) -> Path:
        """Return the concrete private Store path for diagnostics and tests.

        Returns:
            Filesystem path managed by Home Assistant Store.
        """
        return Path(self._store.path)
    @property
    def revision(self) -> int:
        """Return the loaded durable payload revision.

        Returns:
            Monotonically increasing integration payload revision.
        """
        return int(self._require_payload()["revision"])
    @property
    def desired(self) -> dict[str, Any]:
        """Return an isolated persistent desired-state mapping.

        Returns:
            Canonical restorable settings owned by this entry.
        """
        return copy.deepcopy(self._require_payload()["desired"])
    @property
    def last_profile(self) -> str | None:
        """Return the exact optional capture lineage profile.

        Returns:
            Stored parent profile identifier or ``None``.
        """
        return self._require_payload()["last_profile"]
    @property
    def last_applied_profile(self) -> str | None:
        """Return the last fully successful Home Assistant profile application.

        Returns:
            Truthful selector profile identifier or ``None``.
        """
        return self._require_payload()["last_applied_profile"]
    @property
    def desired_active(self) -> bool:
        """Return whether persistent desired ownership may reconcile."""
        return bool(self._require_payload()["desired_active"])

    @property
    def profile_repository(self) -> ProfileRepository:
        """Return the loaded host-owned portable profile repository.

        Returns:
            Store-backed repository using the public client profile engine.

        Raises:
            EntryStoreError: If the Store owner has not been loaded.
        """
        if self._profile_repository is None:
            raise EntryStoreError("entry Store has not been loaded")
        return self._profile_repository

    async def async_load(self) -> None:
        """Load, validate, and initialize one entry's durable Store state.

        Returns:
            None.

        Raises:
            EntryStoreError: If stored data or its profile graph is invalid.
        """
        async with self._lock:
            raw = await self._store.async_load()
            try:
                candidate = (
                    new_store_payload()
                    if raw is None
                    else validate_store_payload(raw)
                )
                repository = build_profile_repository(
                    candidate["profiles"], self._save_profiles
                )
                await validate_profile_repository(repository)
            except UnsupportedStoreSchemaError:
                raise EntryStoreError(
                    "unsupported store schema",
                    fault="unsupported_store",
                ) from None
            except StorePayloadError:
                raise EntryStoreError(
                    "stored integration data is invalid",
                    fault="corrupt_store",
                ) from None
            except Exception:
                raise EntryStoreError(
                    "stored integration data is invalid",
                    fault="corrupt_store",
                ) from None
            if raw is None:
                candidate = await self._persist_candidate(candidate)
            self._payload = candidate
            self._profile_repository = repository

    async def async_save_config(self, config: Mapping[str, Any]) -> None:
        """Persist desired state and lineage from a runtime client config.

        Args:
            config: Complete normalized public client configuration.

        Returns:
            None after durable content verification.
        """
        desired_raw = config.get("desired", {})
        if not isinstance(desired_raw, Mapping):
            raise EntryStoreError("runtime desired state must be an object")
        desired = normalize_settings(desired_raw, require_restorable=True)
        last_profile = config.get("last_profile")
        if last_profile is not None and not isinstance(last_profile, str):
            raise EntryStoreError("runtime last_profile must be a string or null")
        if last_profile is not None:
            await self._require_profile_exists(last_profile)
        await self._commit(
            {"desired": desired, "last_profile": last_profile}
        )

    async def async_set_last_applied_profile(self, name: str | None) -> None:
        """Persist truthful last-successful Home Assistant profile selection.

        Args:
            name: Successful profile identifier, or ``None`` to clear it.

        Returns:
            None after durable content verification.
        """
        if name is not None and not isinstance(name, str):
            raise EntryStoreError("last applied profile must be a string or null")
        if name is not None:
            await self._require_profile_exists(name)
        await self._commit({"last_applied_profile": name})

    async def async_transition_authority(self, authority: str) -> None:
        """Persist safe active/dormant state for one runtime-mode transition.

        Args:
            authority: Canonical authority selected for the loading entry.

        Returns:
            None after durable transition metadata verification.
        """
        payload = self._require_payload()
        previous = payload["last_authority"]
        active = bool(payload["desired_active"])
        if previous == "persistent" and authority != "persistent":
            active = False
        elif authority == "persistent" and not payload["desired"]:
            active = True
        if previous != authority or active != payload["desired_active"]:
            await self._commit(
                {"last_authority": authority, "desired_active": active}
            )

    async def async_set_desired_active(self, active: bool) -> None:
        """Explicitly activate or deactivate retained desired ownership.

        Args:
            active: Replacement reconciliation authorization flag.

        Returns:
            None after durable verification.
        """
        if active != self.desired_active:
            await self._commit({"desired_active": active})

    async def async_remove(self) -> None:
        """Delete only this config entry's private Store document.

        Returns:
            None after Home Assistant removes the targeted Store key.
        """
        async with self._lock:
            await self._store.async_remove()
            self._payload = None
            self._profile_repository = None

    async def _save_profiles(self, documents: dict[str, dict[str, Any]]) -> None:
        """Commit a complete validated portable profile catalogue.

        Args:
            documents: Candidate catalogue already validated by the profile engine.

        Returns:
            None after durable next-revision verification.
        """
        await self._commit({"profiles": documents})

    async def _require_profile_exists(self, name: str) -> None:
        """Fail before mutation when a profile marker has no document.

        Args:
            name: Profile identifier proposed for durable marker state.

        Returns:
            None when the profile exists.
        """
        if name not in await self.profile_repository.list_profiles():
            raise EntryStoreError(f"profile {name!r} does not exist")

    async def _commit(self, changes: Mapping[str, Any]) -> None:
        """Durably replace selected payload fields before exposing them.

        Args:
            changes: Complete replacements for selected top-level payload fields.

        Returns:
            None after exact durable readback.
        """
        async with self._lock:
            candidate = copy.deepcopy(self._require_payload())
            candidate.update(copy.deepcopy(dict(changes)))
            candidate = await self._persist_candidate(candidate)
            self._payload = candidate

    async def _persist_candidate(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Write and read back one next-revision payload for durable proof.

        Args:
            candidate: Complete payload with the currently visible revision.

        Returns:
            Persisted isolated payload with its revision incremented once.

        Raises:
            EntryStoreError: If save or exact readback verification fails.
        """
        saved = copy.deepcopy(dict(candidate))
        saved["revision"] = int(saved["revision"]) + 1
        await self._store.async_save(saved)
        try:
            persisted = await self._store.async_load()
        except Exception as exc:
            raise EntryStoreError("durable verification failed after Store save") from exc
        if persisted != saved:
            raise EntryStoreError("durable verification failed after Store save")
        return saved

    def _require_payload(self) -> dict[str, Any]:
        """Return loaded internal payload or fail closed before initialization.

        Returns:
            Mutable internal payload owned by this transaction object.

        Raises:
            EntryStoreError: If :meth:`async_load` has not completed.
        """
        if self._payload is None:
            raise EntryStoreError("entry Store has not been loaded")
        return self._payload
