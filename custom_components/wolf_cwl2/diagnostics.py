"""Privacy-by-construction diagnostics for one loaded WOLF CWL-2 entry."""

from __future__ import annotations

from importlib.metadata import version
from typing import Any, Final

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.loader import async_get_integration

from .const import (
    CONF_ALLOW_APPLIANCE_RESET,
    CONF_AUTHORITY,
    CONF_FAST_INTERVAL,
    CONF_READ_EXTENSION,
    CONF_READ_HOLDING,
    CONF_RECONCILE_INTERVAL,
    CONF_SLOW_INTERVAL,
    CONF_STATIC_INTERVAL,
    DEFAULT_OPTIONS,
    DOMAIN,
)
from .runtime import WolfCWL2ConfigEntry

REDACT_KEYS: Final = {
    "address_offset",
    "desired",
    "device_id",
    "entry_id",
    "host",
    "last_profile",
    "port",
    "profiles",
    "raw",
    "serial_number",
    "unique_id",
    "value",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
) -> dict[str, Any]:
    """Return useful operational categories without protected source values.

    Args:
        hass: Home Assistant instance owning integration metadata.
        entry: Loaded config entry whose runtime is summarized.

    Returns:
        Redacted JSON-safe version, policy, health, tier, and count data.
    """
    integration = await async_get_integration(hass, DOMAIN)
    runtime = entry.runtime_data
    policy = {**DEFAULT_OPTIONS, **dict(entry.options)}
    snapshot = runtime.controller.snapshot()
    states = snapshot["values"]
    available_keys = sorted(
        key for key, state in states.items() if bool(state["available"])
    )
    error_keys = sorted(
        key for key, state in states.items() if state["error"] is not None
    )
    successful_tiers = {
        tier for tier, _timestamp in runtime.coordinator.data.tier_last_success
    }
    data: dict[str, Any] = {
        "versions": {
            "integration": integration.version,
            "client": version("wolf-325"),
        },
        "policy": {
            "authority": policy[CONF_AUTHORITY],
            "fast_interval_seconds": policy[CONF_FAST_INTERVAL],
            "slow_interval_seconds": policy[CONF_SLOW_INTERVAL],
            "static_interval_seconds": policy[CONF_STATIC_INTERVAL],
            "reconcile_interval_seconds": policy[CONF_RECONCILE_INTERVAL],
            "read_holding_registers": policy[CONF_READ_HOLDING],
            "read_extension_registers": policy[CONF_READ_EXTENSION],
            "appliance_reset_opt_in": policy[CONF_ALLOW_APPLIANCE_RESET],
        },
        "runtime": {
            "connected": runtime.controller.connected,
            "connection_generation": snapshot["connection_generation"],
            "coordinator_last_update_success": (
                runtime.coordinator.last_update_success
            ),
            "stopping": runtime.stopping,
            "scheduler_retained": runtime.scheduler_unsubscribe is not None,
            "client_background_scheduling": False,
        },
        "tiers": {
            tier: {
                "has_succeeded": tier in successful_tiers,
                "fresh": runtime.coordinator.tier_is_fresh(tier),
            }
            for tier in ("fast", "slow", "static")
        },
        "availability": {
            "available_count": len(available_keys),
            "unavailable_count": len(states) - len(available_keys),
            "unavailable_keys": sorted(set(states) - set(available_keys)),
            "error_count": len(error_keys),
            "error_keys": error_keys,
            "reconcile_error_keys": list(
                runtime.coordinator.data.reconcile_errors
            ),
            "desired_pending_count": runtime.coordinator.data.desired_pending,
        },
    }
    return async_redact_data(data, REDACT_KEYS)


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return the same safe one-appliance summary from the device surface.

    Args:
        hass: Home Assistant instance owning integration metadata.
        entry: Loaded config entry owning exactly one appliance.
        device: Device-registry entry selected by Home Assistant.

    Returns:
        Redacted config-entry diagnostics without device identifiers.
    """
    if entry.entry_id not in device.config_entries:
        raise ValueError("device does not belong to the selected config entry")
    return await async_get_config_entry_diagnostics(hass, entry)
