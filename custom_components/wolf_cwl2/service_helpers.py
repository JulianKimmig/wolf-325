"""Shared loaded-entry resolution for integration-level HA actions."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .runtime import EntryRuntime

CONF_CONFIG_ENTRY_ID = "config_entry_id"


def runtime_for(hass: HomeAssistant, call: ServiceCall) -> EntryRuntime:
    """Resolve one loaded integration runtime from a service target.

    Args:
        hass: Home Assistant instance owning config entries.
        call: Validated call containing a config-entry identifier.

    Returns:
        Loaded typed entry runtime.

    Raises:
        HomeAssistantError: If the target is absent, unloaded, or another domain.
    """
    entry = hass.config_entries.async_get_entry(call.data[CONF_CONFIG_ENTRY_ID])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="entry_unavailable",
        )
    return entry.runtime_data
