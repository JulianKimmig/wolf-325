"""Home Assistant integration for WOLF CWL-2 ventilation appliances."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.typing import ConfigType

from wolf_325 import WolfCWL2

from .const import CONF_ALLOW_APPLIANCE_RESET, CONF_AUTHORITY, DEFAULT_OPTIONS
from .coordinator import WolfCWL2Coordinator
from .entry_config import build_client_config
from .runtime import EntryRuntime, WolfCWL2ConfigEntry
from .repairs import clear_entry_issue, create_entry_issue
from .services import async_register_services
from .storage import EntryStore, EntryStoreError

PLATFORMS = (
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration package without opening a device.

    Args:
        hass: Home Assistant instance that owns integration lifecycle.
        config: Complete Home Assistant YAML configuration mapping.

    Returns:
        ``True`` because YAML setup has no integration-owned resources.
    """
    async_register_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
) -> bool:
    """Load one isolated runtime and complete its first confirmed poll.

    Args:
        hass: Home Assistant instance that owns integration lifecycle.
        entry: Config entry representing one verified appliance.

    Returns:
        ``True`` after identity verification and platform forwarding.
    """
    store = EntryStore(hass, entry.entry_id)
    try:
        await store.async_load()
    except EntryStoreError as exc:
        create_entry_issue(hass, exc.fault or "corrupt_store", entry.entry_id)
        raise ConfigEntryError("stored integration data requires recovery") from None
    clear_entry_issue(hass, "corrupt_store", entry.entry_id)
    clear_entry_issue(hass, "unsupported_store", entry.entry_id)
    policy = {**DEFAULT_OPTIONS, **dict(entry.options)}
    await store.async_transition_authority(str(policy[CONF_AUTHORITY]))
    config = build_client_config(entry.data, policy, store)
    controller = WolfCWL2.from_config(
        config,
        save_callback=store.async_save_config,
        profile_repository=store.profile_repository,
    )
    operation_lock = asyncio.Lock()
    coordinator = WolfCWL2Coordinator(
        hass,
        entry,
        controller,
        operation_lock,
        policy,
        entry.unique_id or "",
        store=store,
        authority=str(policy[CONF_AUTHORITY]),
    )
    try:
        await controller.start(
            restore=False,
            background=False,
            read_only=policy[CONF_AUTHORITY] == "monitor_only",
            initial_poll=False,
        )
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await controller.stop()
        raise
    scheduler_unsubscribe = coordinator.async_add_listener(_retain_scheduler)
    entry.runtime_data = EntryRuntime(
        controller=controller,
        coordinator=coordinator,
        store=store,
        operation_lock=operation_lock,
        authority=str(policy[CONF_AUTHORITY]),
        profile_names=tuple(await store.profile_repository.list_profiles()),
        last_applied_profile=(
            store.last_applied_profile
            if policy[CONF_AUTHORITY] == "persistent"
            else None
        ),
        scheduler_unsubscribe=scheduler_unsubscribe,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
) -> bool:
    """Migrate an actual older config-entry schema without device I/O.

    Args:
        hass: Home Assistant instance owning config-entry persistence.
        entry: Existing entry requiring schema migration.

    Returns:
        ``True`` after a supported migration, otherwise ``False``.
    """
    if entry.version != 1 or entry.minor_version != 1:
        return False
    options = dict(entry.options)
    options[CONF_ALLOW_APPLIANCE_RESET] = False
    hass.config_entries.async_update_entry(
        entry,
        options=options,
        version=1,
        minor_version=2,
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
) -> bool:
    """Unload platforms, scheduler, transport, and only this entry's runtime.

    Args:
        hass: Home Assistant instance that owns integration lifecycle.
        entry: Config entry being unloaded.

    Returns:
        Whether all platforms unloaded and runtime cleanup completed.
    """
    runtime = entry.runtime_data
    runtime.stopping = True
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        runtime.stopping = False
        return False
    runtime.scheduler_unsubscribe()
    await runtime.coordinator.async_shutdown()
    async with runtime.operation_lock:
        await runtime.controller.stop()
    return True


async def async_remove_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove only the deleted config entry's private Store document.

    Args:
        hass: Home Assistant instance owning Store persistence.
        entry: Config entry already selected for permanent removal.

    Returns:
        None after targeted Store removal.
    """
    store = EntryStore(hass, entry.entry_id)
    await store.async_remove()


def _retain_scheduler() -> None:
    """Retain coordinator cadence even when every entity is disabled.

    Returns:
        None; the callback exists solely as an entry-lifetime listener.
    """
