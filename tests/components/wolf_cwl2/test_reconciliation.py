"""Persistent reconciliation, dormancy, and ownership workflow tests."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(authority: str = "persistent") -> MockConfigEntry:
    """Build one serial-backed entry in the requested authority mode.

    Args:
        authority: Canonical authority option.

    Returns:
        Detached config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Persistent ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={**DEFAULT_OPTIONS, "authority": authority},
    )


def _entity_id(hass: HomeAssistant, domain: str, unique_suffix: str) -> str:
    """Resolve a runtime entity through its stable unique suffix.

    Args:
        hass: Home Assistant instance owning the registry.
        domain: Native platform domain.
        unique_suffix: Stable integration-owned unique-ID suffix.

    Returns:
        Registered entity ID.
    """
    entity_id = er.async_get(hass).async_get_entity_id(
        domain, DOMAIN, f"123456789012_{unique_suffix}"
    )
    assert entity_id is not None
    return entity_id


async def _reload_with_authority(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    authority: str,
) -> None:
    """Update one authority option and complete its targeted reload.

    Args:
        hass: Home Assistant test instance.
        entry: Loaded entry to transition.
        authority: Replacement canonical authority mode.

    Returns:
        None after reload completion.
    """
    hass.config_entries.async_update_entry(
        entry,
        options={**entry.options, "authority": authority},
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()


async def test_leaving_persistent_makes_desired_dormant_until_explicit_resume(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Never silently reassert retained ownership after a mode round trip.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    airflow = _entity_id(hass, "number", "remote_airflow_m3h")
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": airflow, "value": 200},
        blocking=True,
    )
    assert entry.runtime_data.store.desired_active

    await _reload_with_authority(hass, entry, "temporary")
    assert entry.runtime_data.store.desired == {"remote_airflow_m3h": 200}
    assert not entry.runtime_data.store.desired_active
    fake_gateway.writes.clear()
    fake_gateway.holding_words[8002] = 100

    await _reload_with_authority(hass, entry, "persistent")
    assert not entry.runtime_data.store.desired_active
    assert fake_gateway.writes == []

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity_id(hass, "button", "resume_desired")},
        blocking=True,
    )
    assert entry.runtime_data.store.desired_active
    assert fake_gateway.holding_words[8002] == 200


async def test_coordinator_reconciles_drift_only_when_persistent_and_active(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Run due reconciliation behind the coordinator operation lock.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": _entity_id(hass, "number", "remote_airflow_m3h"),
            "value": 250,
        },
        blocking=True,
    )
    fake_gateway.writes.clear()
    fake_gateway.holding_words[8002] = 100
    entry.runtime_data.coordinator._next_reconcile = 0.0

    await entry.runtime_data.coordinator.async_request_refresh()
    assert fake_gateway.holding_words[8002] == 250
    assert fake_gateway.writes == [(8002, 250, 20)]


async def test_clear_desired_releases_ownership_without_device_write(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Clear all desired ownership without replacing live appliance values.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": _entity_id(hass, "number", "remote_airflow_m3h"),
            "value": 170,
        },
        blocking=True,
    )
    fake_gateway.writes.clear()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": _entity_id(hass, "button", "clear_desired")},
        blocking=True,
    )
    assert entry.runtime_data.store.desired == {}
    assert not entry.runtime_data.store.desired_active
    assert fake_gateway.writes == []
    assert fake_gateway.holding_words[8002] == 170
