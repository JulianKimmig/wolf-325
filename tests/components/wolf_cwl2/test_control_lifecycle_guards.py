"""Lifecycle and availability guard tests for native Home Assistant controls."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN
from custom_components.wolf_cwl2.mutations import async_set_setting

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _setup_temporary_entry(
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Load one temporary-authority entry for lifecycle guards.

    Args:
        hass: Home Assistant instance that owns the config entry.

    Returns:
        Loaded serial-backed config entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Guarded ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={**DEFAULT_OPTIONS, "authority": "temporary"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _airflow_entity_id(hass: HomeAssistant) -> str:
    """Resolve the stable direct-airflow number entity.

    Args:
        hass: Home Assistant instance owning the entity registry.

    Returns:
        Registered number entity ID.
    """
    entity_id = er.async_get(hass).async_get_entity_id(
        "number", DOMAIN, "123456789012_remote_airflow_m3h"
    )
    assert entity_id is not None
    return entity_id


async def _request_airflow(hass: HomeAssistant) -> None:
    """Request one valid direct-airflow value through the native service.

    Args:
        hass: Home Assistant instance owning the entity service.

    Returns:
        None after the blocking service call completes.
    """
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": _airflow_entity_id(hass), "value": 200},
        blocking=True,
    )


async def test_stopping_entry_rejects_control_before_external_io(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject new work once entry teardown has begun.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = await _setup_temporary_entry(hass)
    entry.runtime_data.stopping = True

    with pytest.raises(HomeAssistantError, match="stopping"):
        await _request_airflow(hass)

    assert fake_gateway.writes == []


async def test_failed_coordinator_state_rejects_control_before_external_io(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject controls while the latest coordinated refresh is unavailable.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = await _setup_temporary_entry(hass)
    entry.runtime_data.coordinator.last_update_success = False

    with pytest.raises(HomeAssistantError, match="unavailable"):
        await async_set_setting(
            entry.runtime_data,
            "remote_airflow_m3h",
            200,
        )

    assert fake_gateway.writes == []


async def test_disconnected_transport_rejects_control_before_external_io(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject controls when the retained external client is disconnected.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = await _setup_temporary_entry(hass)
    assert fake_gateway.clients
    fake_gateway.clients[-1].connected = False

    with pytest.raises(HomeAssistantError, match="disconnected"):
        await async_set_setting(
            entry.runtime_data,
            "remote_airflow_m3h",
            200,
        )

    assert fake_gateway.writes == []
