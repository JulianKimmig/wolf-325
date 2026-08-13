"""Config-entry schema migration tests for the WOLF CWL-2 integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2 import async_migrate_entry
from custom_components.wolf_cwl2.config_flow import WolfCWL2ConfigFlow
from custom_components.wolf_cwl2.const import DOMAIN

from .test_config_flow import CONNECTION, DEFAULT_OPTIONS


async def test_minor_two_migration_adds_reset_opt_in_without_other_changes(
    hass: HomeAssistant,
) -> None:
    """Migrate the actual v1.1 option document to the v1.2 contract.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    legacy_options = {
        key: value
        for key, value in DEFAULT_OPTIONS.items()
        if key != "allow_appliance_reset"
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456789012",
        data=CONNECTION,
        options=legacy_options,
        version=1,
        minor_version=1,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == WolfCWL2ConfigFlow.VERSION == 1
    assert entry.minor_version == WolfCWL2ConfigFlow.MINOR_VERSION == 2
    assert entry.data == CONNECTION
    assert entry.options == DEFAULT_OPTIONS


async def test_migration_rejects_unknown_forward_entry_schema(
    hass: HomeAssistant,
) -> None:
    """Leave a future entry untouched instead of guessing a downgrade.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456789012",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
        version=99,
        minor_version=1,
    )
    entry.add_to_hass(hass)

    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 99
    assert entry.data == CONNECTION
    assert entry.options == DEFAULT_OPTIONS
