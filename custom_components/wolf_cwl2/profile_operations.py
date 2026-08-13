"""Serialized profile application using the public client profile engine."""

from __future__ import annotations

import logging

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from wolf_325 import BulkWriteError, CommunicationError, ProfileError, RegisterError

from .const import DOMAIN
from .mutations import publish_confirmed_state
from .runtime import EntryRuntime

LOGGER = logging.getLogger(__name__)


async def async_apply_profile(runtime: EntryRuntime, name: str) -> None:
    """Apply one HA-owned profile under mode and operation-lock policy.

    Args:
        runtime: Per-entry resource, authority, and profile-state owner.
        name: Existing Store-owned profile identifier.

    Returns:
        None after all writes verify and selector truth advances.

    Raises:
        ServiceValidationError: If mode, dormancy, or profile input rejects.
        HomeAssistantError: If live application is incomplete.
    """
    async with runtime.operation_lock:
        if runtime.stopping:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="entry_stopping"
            )
        if runtime.authority == "monitor_only":
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="monitor_only"
            )
        if name not in runtime.profile_names:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_profile",
                translation_placeholders={"name": name},
            )
        if runtime.authority == "persistent" and not runtime.store.desired_active:
            if runtime.store.desired:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="desired_dormant",
                )
            await runtime.store.async_set_desired_active(True)
        try:
            await runtime.controller.apply_profile(
                name,
                persist=runtime.authority == "persistent",
            )
        except (CommunicationError, BulkWriteError) as exc:
            failed_keys = (
                tuple(sorted(exc.errors))
                if isinstance(exc, BulkWriteError)
                else ()
            )
            LOGGER.warning(
                "profile application incomplete; failed setting keys: %s",
                failed_keys,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="profile_apply_incomplete",
            ) from exc
        except (ProfileError, RegisterError) as exc:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_profile",
                translation_placeholders={"detail": str(exc)},
            ) from exc
        if runtime.authority == "persistent":
            await runtime.store.async_set_last_applied_profile(name)
            runtime.coordinator.defer_reconciliation()
        runtime.last_applied_profile = name
        publish_confirmed_state(runtime)
