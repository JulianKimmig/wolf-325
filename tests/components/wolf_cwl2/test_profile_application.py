"""Native Home Assistant profile selection and application tests."""

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


def _entry(authority: str) -> MockConfigEntry:
    """Build one entry for a profile authority test.

    Args:
        authority: Canonical runtime authority mode.

    Returns:
        Detached serial-backed config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Profile ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={**DEFAULT_OPTIONS, "authority": authority},
    )


def _profile_select(hass: HomeAssistant) -> str:
    """Resolve the synthetic profile selector entity ID.

    Args:
        hass: Home Assistant instance owning the registry.

    Returns:
        Registered profile selector entity ID.
    """
    entity_id = er.async_get(hass).async_get_entity_id(
        "select", DOMAIN, "123456789012_profile"
    )
    assert entity_id is not None
    return entity_id


async def test_profile_selector_exposes_ha_owned_catalogue(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Register one stable selector with the seeded Store profile names.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("monitor_only")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get(_profile_select(hass))
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["options"] == [
        "away",
        "boost",
        "night",
        "normal",
        "summer-night",
    ]


async def test_monitor_profile_rejects_before_store_or_modbus_mutation(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject profile application completely in monitor-only mode.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("monitor_only")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    revision = entry.runtime_data.store.revision

    with pytest.raises(ServiceValidationError, match="monitor"):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": _profile_select(hass), "option": "normal"},
            blocking=True,
        )
    assert entry.runtime_data.store.revision == revision
    assert fake_gateway.writes == []


async def test_temporary_profile_is_runtime_only_and_fully_verified(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Apply a profile live without desired, lineage, or durable selector state.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("temporary")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": _profile_select(hass), "option": "normal"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.desired == {}
    assert entry.runtime_data.store.last_profile is None
    assert entry.runtime_data.store.last_applied_profile is None
    assert hass.states.get(_profile_select(hass)).state == "normal"
    assert [item[0] for item in fake_gateway.writes] == [8001, 8003, 8000]


async def test_persistent_profile_commits_lineage_and_success_marker(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Persist complete desired intent before publishing successful selection.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("persistent")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": _profile_select(hass), "option": "night"},
        blocking=True,
    )
    await hass.async_block_till_done()

    store = entry.runtime_data.store
    assert store.desired == {
        "remote_control_mode": "level",
        "remote_standby": False,
        "remote_ventilation_level": "low",
    }
    assert store.last_profile == "night"
    assert store.last_applied_profile == "night"
    assert store.desired_active
    assert hass.states.get(_profile_select(hass)).state == "night"


async def test_persistent_partial_profile_keeps_intent_without_success_marker(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Report partial I/O while retaining full desired lineage for retry.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.write_failure_addresses = {8003}
    entry = _entry("persistent")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    with pytest.raises(HomeAssistantError, match="fully confirmed"):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": _profile_select(hass), "option": "night"},
            blocking=True,
        )

    store = entry.runtime_data.store
    assert store.desired == {
        "remote_control_mode": "level",
        "remote_standby": False,
        "remote_ventilation_level": "low",
    }
    assert store.last_profile == "night"
    assert store.last_applied_profile is None
    assert store.desired_active is True
    assert entry.runtime_data.last_applied_profile is None
    assert hass.states.get(_profile_select(hass)).state == "unknown"
    assert [write[0] for write in fake_gateway.writes] == [8001]
    assert [attempt[0] for attempt in fake_gateway.write_attempts] == [
        8001,
        8003,
        8003,
        8003,
    ]
