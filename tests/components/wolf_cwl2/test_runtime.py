"""Tests for config-entry runtime, first refresh, entities, and isolation."""

from __future__ import annotations

import asyncio

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(
    serial: str = "123456789012",
    *,
    device_id: int = 20,
) -> MockConfigEntry:
    """Build one configured entry for runtime tests.

    Args:
        serial: Verified config-entry identity.
        device_id: Downstream Modbus unit identifier.

    Returns:
        Detached mock config entry with canonical data and options.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"WOLF CWL-2 {serial}",
        unique_id=serial,
        data={**CONNECTION, "device_id": device_id},
        options=DEFAULT_OPTIONS,
    )


async def test_setup_polls_once_publishes_sensor_and_unloads_cleanly(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Deliver one confirmed airflow entity with no client background tasks.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.input_words[4032] = 170
    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    runtime = entry.runtime_data
    assert runtime.controller.get_value("serial_number") == "123456789012"
    assert runtime.controller._tasks == []
    assert runtime.coordinator.data.refreshed_tiers == ("fast", "slow", "static")
    assert fake_gateway.reads
    assert fake_gateway.holding_reads

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        "123456789012_supply_airflow_actual_m3h",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "170"
    assert state.attributes["unit_of_measurement"] == "m³/h"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert all(not client.connected for client in fake_gateway.clients)


async def test_identity_mismatch_retries_without_forwarding_entities(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Fail setup closed when the first complete poll reports another serial.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("999999999999")
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not er.async_get(hass).entities.get_entries_for_config_entry_id(
        entry.entry_id
    )
    assert all(not client.connected for client in fake_gateway.clients)


async def test_two_entries_keep_runtime_and_unload_isolated(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Load two serial identities and unload only the selected runtime.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    first = _entry()
    first.add_to_hass(hass)
    assert await hass.config_entries.async_setup(first.entry_id)

    fake_gateway.serial = "999999999999"
    fake_gateway.apply_identity()
    second = _entry("999999999999", device_id=21)
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    first_runtime = first.runtime_data
    second_runtime = second.runtime_data
    assert first_runtime is not second_runtime
    assert first_runtime.operation_lock is not second_runtime.operation_lock
    assert first_runtime.store.storage_key != second_runtime.store.storage_key

    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    assert first.state is ConfigEntryState.NOT_LOADED
    assert second.state is ConfigEntryState.LOADED
    assert second_runtime.controller.connected


async def test_scheduler_remains_owned_when_entity_is_disabled(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Retain one coordinator listener after all platform entities are disabled.

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
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert entries
    for registry_entry in entries:
        registry.async_update_entity(
            registry_entry.entity_id,
            disabled_by=er.RegistryEntryDisabler.USER,
        )

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    runtime = entry.runtime_data
    assert len(runtime.coordinator._listeners) == 1
    assert runtime.coordinator._unsub_refresh is not None


async def test_unload_waits_for_inflight_operation_and_drains_resources(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Drain the whole-operation lock before transport and scheduler teardown.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    runtime = entry.runtime_data
    await runtime.operation_lock.acquire()

    unload = asyncio.create_task(hass.config_entries.async_unload(entry.entry_id))
    for _ in range(20):
        if runtime.stopping:
            break
        await asyncio.sleep(0)
    assert runtime.stopping
    assert not unload.done()
    assert runtime.controller.connected

    runtime.operation_lock.release()
    assert await asyncio.wait_for(unload, timeout=1)
    assert not runtime.controller.connected
    assert runtime.controller._tasks == []
    assert runtime.coordinator._listeners == {}
    assert runtime.coordinator._unsub_refresh is None
    assert all(not client.connected for client in fake_gateway.clients)


async def test_blocked_entry_does_not_delay_another_entry_refresh(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Keep per-entry locks and transports independent under blocked I/O.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake with per-device blocking.

    Returns:
        None.
    """
    first = _entry(device_id=20)
    second = _entry(device_id=21)
    first.add_to_hass(hass)
    assert await hass.config_entries.async_setup(first.entry_id)
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    first.runtime_data.coordinator._next_due = {
        tier: 0.0 for tier in ("fast", "slow", "static")
    }
    second.runtime_data.coordinator._next_due = {
        tier: 0.0 for tier in ("fast", "slow", "static")
    }
    fake_gateway.blocked_device_id = 20

    blocked_refresh = asyncio.create_task(
        first.runtime_data.coordinator.async_refresh()
    )
    await asyncio.wait_for(fake_gateway.block_started.wait(), timeout=1)
    assert not blocked_refresh.done()
    await asyncio.wait_for(
        second.runtime_data.coordinator.async_refresh(),
        timeout=1,
    )
    assert second.runtime_data.coordinator.last_update_success

    fake_gateway.release_block.set()
    await asyncio.wait_for(blocked_refresh, timeout=1)
    assert first.runtime_data.coordinator.last_update_success
