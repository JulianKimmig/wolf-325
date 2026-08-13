"""Response-capable Home Assistant profile preview and capture actions."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from wolf_325 import ProfileChanges, ProfileError

from .const import DOMAIN
from .mutations import publish_confirmed_state
from .reset_services import async_register_reset_services
from .runtime import EntryRuntime
from .service_helpers import CONF_CONFIG_ENTRY_ID, runtime_for

PREVIEW_SCHEMA = vol.Schema({vol.Required(CONF_CONFIG_ENTRY_ID): cv.string})
SAVE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required("name"): cv.string,
        vol.Optional("description", default=""): cv.string,
        vol.Optional("overwrite", default=False): cv.boolean,
        vol.Optional("expected_revision"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register profile actions once for the integration domain.

    Args:
        hass: Home Assistant instance owning the service registry.

    Returns:
        None after synchronous service registration.
    """
    async def preview(call: ServiceCall) -> dict[str, Any]:
        """Bind the owning Home Assistant instance to a preview call.

        Args:
            call: Validated response-capable service call.

        Returns:
            Exact profile capture preview response.
        """
        return await _async_preview_profile_capture(hass, call)

    async def save(call: ServiceCall) -> dict[str, Any]:
        """Bind the owning Home Assistant instance to a save call.

        Args:
            call: Validated response-capable service call.

        Returns:
            Saved profile metadata response.
        """
        return await _async_save_profile(hass, call)

    hass.services.async_register(
        DOMAIN,
        "preview_profile_capture",
        preview,
        schema=PREVIEW_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    async_register_reset_services(hass)
    hass.services.async_register(
        DOMAIN,
        "save_profile",
        save,
        schema=SAVE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def _async_preview_profile_capture(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Return exact TUI-equivalent desired-state capture changes.

    Args:
        hass: Home Assistant instance owning config entries.
        call: Validated Home Assistant service call.

    Returns:
        JSON-safe delta, lineage, change flag, and Store revision.
    """
    runtime = runtime_for(hass, call)
    async with runtime.operation_lock:
        _require_persistent(runtime)
        changes = await runtime.controller.preview_profile_changes()
        return _changes_response(changes, runtime.store.revision)


async def _async_save_profile(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Atomically save current persistent desired changes as one profile.

    Args:
        hass: Home Assistant instance owning config entries.
        call: Validated Home Assistant service call.

    Returns:
        JSON-safe saved profile metadata and exact Store revision.
    """
    runtime = runtime_for(hass, call)
    async with runtime.operation_lock:
        _require_persistent(runtime)
        expected = call.data.get("expected_revision")
        if expected is not None and expected != runtime.store.revision:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="store_revision_changed",
            )
        try:
            saved = await runtime.controller.save_profile(
                call.data["name"],
                description=call.data["description"],
                overwrite=call.data["overwrite"],
            )
        except ProfileError as exc:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_profile",
                translation_placeholders={"detail": str(exc)},
            ) from exc
        runtime.profile_names = tuple(
            await runtime.store.profile_repository.list_profiles()
        )
        publish_confirmed_state(runtime)
        return {
            "name": saved.name,
            "description": saved.description,
            **_changes_response(saved.changes, runtime.store.revision),
        }


def _require_persistent(runtime: EntryRuntime) -> None:
    """Reject profile capture outside persistent authority.

    Args:
        runtime: Target entry runtime.

    Returns:
        None when capture semantics are durable and permitted.
    """
    if runtime.stopping or runtime.authority != "persistent":
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="persistent_required",
        )


def _changes_response(changes: ProfileChanges, revision: int) -> dict[str, Any]:
    """Convert public profile changes to a stable HA action response.

    Args:
        changes: Public exact desired-state delta.
        revision: Current integration Store revision.

    Returns:
        JSON-safe response without live telemetry or raw values.
    """
    return {
        "base": changes.extends,
        "settings": dict(changes.settings),
        "unset": list(changes.unset),
        "replace": changes.replace,
        "has_changes": changes.has_changes,
        "revision": revision,
    }
