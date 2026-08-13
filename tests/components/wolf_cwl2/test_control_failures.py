"""Failure-path tests for authority-gated Home Assistant controls."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _persistent_entry() -> MockConfigEntry:
    """Build one serial-backed persistent-authority entry.

    Returns:
        Detached Home Assistant config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Failure-path ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={**DEFAULT_OPTIONS, "authority": "persistent"},
    )


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


async def _set_airflow(hass: HomeAssistant, value: int) -> None:
    """Invoke the native number service for direct airflow.

    Args:
        hass: Home Assistant instance owning the entity service.
        value: Requested cubic-metres-per-hour setpoint.

    Returns:
        None after the blocking service call completes.
    """
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": _airflow_entity_id(hass), "value": value},
        blocking=True,
    )


async def test_persistent_transport_failure_keeps_queued_desired_and_actual_state(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Keep durable intent queued when the external write cannot complete.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.holding_words[8002] = 170
    fake_gateway.write_failure_addresses = {8002}
    entry = _persistent_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    before = hass.states.get(_airflow_entity_id(hass))
    assert before is not None

    with pytest.raises(HomeAssistantError, match="confirm"):
        await _set_airflow(hass, 250)

    assert entry.runtime_data.store.desired == {"remote_airflow_m3h": 250}
    assert entry.runtime_data.store.desired_active is True
    assert hass.states.get(_airflow_entity_id(hass)).state == before.state
    assert fake_gateway.holding_words[8002] == 170
    assert fake_gateway.writes == []
    assert [attempt[0] for attempt in fake_gateway.write_attempts] == [8002] * 3


async def test_verification_mismatch_never_publishes_requested_value(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Retain confirmed state when write read-back differs from the request.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.holding_words[8002] = 170
    fake_gateway.write_readback_words = {8002: 170}
    entry = _persistent_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="confirm"):
        await _set_airflow(hass, 250)

    assert entry.runtime_data.store.desired == {"remote_airflow_m3h": 250}
    assert fake_gateway.writes == [(8002, 250, 20)]
    assert fake_gateway.holding_words[8002] == 170
    assert hass.states.get(_airflow_entity_id(hass)).state == "170"


async def test_identity_change_rejects_before_write(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject a control after fresh cache identity differs from the entry.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _persistent_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    fake_gateway.serial = "999999999999"
    fake_gateway.apply_identity()
    await entry.runtime_data.controller.refresh("serial_number")

    with pytest.raises(HomeAssistantError, match="identity"):
        await _set_airflow(hass, 200)

    assert entry.runtime_data.store.desired == {}
    assert fake_gateway.writes == []


async def test_dormant_desired_rejects_new_persistent_control(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Require explicit resume or clear before extending dormant ownership.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _persistent_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await _set_airflow(hass, 170)
    await entry.runtime_data.store.async_set_desired_active(False)
    writes_before = list(fake_gateway.writes)

    with pytest.raises(ServiceValidationError, match="dormant"):
        await _set_airflow(hass, 200)

    assert entry.runtime_data.store.desired == {"remote_airflow_m3h": 170}
    assert entry.runtime_data.store.desired_active is False
    assert fake_gateway.writes == writes_before


async def test_relational_setting_rejects_against_fresh_confirmed_peers(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject an invalid ordered airflow preset before persistence or write.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _persistent_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    low_entity_id = er.async_get(hass).async_get_entity_id(
        "number", DOMAIN, "123456789012_flow_preset_low_m3h"
    )
    assert low_entity_id is not None

    with pytest.raises(ServiceValidationError, match="invalid"):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": low_entity_id, "value": 100},
            blocking=True,
        )

    assert entry.runtime_data.store.desired == {}
    assert fake_gateway.writes == []
