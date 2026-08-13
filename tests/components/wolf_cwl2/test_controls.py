"""Authority and native-control behavior tests for the integration."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN
from custom_components.wolf_cwl2.entity_catalogue import ENTITY_SPECS

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(authority: str) -> MockConfigEntry:
    """Build one entry in the requested authority mode.

    Args:
        authority: Canonical monitor, temporary, or persistent mode.

    Returns:
        Detached config entry with default polling policy.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Controlled ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={**DEFAULT_OPTIONS, "authority": authority},
    )


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    """Resolve one stable registry entity ID by canonical setting key.

    Args:
        hass: Home Assistant instance owning the entity registry.
        platform: Native control platform domain.
        key: Canonical client register key.

    Returns:
        Registered Home Assistant entity ID.
    """
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"123456789012_{key}"
    )
    assert entity_id is not None
    return entity_id


async def test_all_safe_controls_register_on_native_platforms(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Expose every reviewed safe writable disposition and no action register.

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

    entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    expected = {
        f"123456789012_{key}": spec.platform
        for key, spec in ENTITY_SPECS.items()
        if spec.platform != "action"
    }
    assert len(entries) == 157
    actual = {item.unique_id: item.domain for item in entries}
    assert {key: actual[key] for key in expected} == expected
    assert {
        item.unique_id for item in entries if item.domain == "button"
    } == {
        "123456789012_clear_desired",
        "123456789012_resume_desired",
    }
    assert actual["123456789012_profile"] == "select"
    assert _entity_id(hass, "number", "remote_airflow_m3h")
    assert _entity_id(hass, "select", "remote_control_mode")
    assert _entity_id(hass, "switch", "remote_standby")


async def test_monitor_mode_rejects_before_store_or_modbus_mutation(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Keep visible controls inert in monitor-only authority.

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
    revision = entry.runtime_data.store.revision

    with pytest.raises(ServiceValidationError, match="monitor"):
        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": _entity_id(hass, "number", "remote_airflow_m3h"),
                "value": 200,
            },
            blocking=True,
        )
    assert entry.runtime_data.store.revision == revision
    assert entry.runtime_data.store.desired == {}
    assert fake_gateway.writes == []


async def test_temporary_number_select_and_switch_write_confirmed_state_only(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Write and verify native controls without creating desired ownership.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("temporary")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": _entity_id(hass, "number", "remote_airflow_m3h"),
            "value": 200,
        },
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": _entity_id(hass, "select", "remote_control_mode"),
            "option": "airflow",
        },
        blocking=True,
    )
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": _entity_id(hass, "switch", "remote_standby")},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.desired == {}
    assert [address for address, _, _ in fake_gateway.writes] == [8002, 8000, 8003]
    assert hass.states.get(_entity_id(hass, "number", "remote_airflow_m3h")).state == "200"
    assert hass.states.get(_entity_id(hass, "select", "remote_control_mode")).state == "airflow"
    assert hass.states.get(_entity_id(hass, "switch", "remote_standby")).state == "on"


async def test_persistent_control_commits_desired_before_verified_write(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Persist ownership and publish only the verified device result.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("persistent")
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
    assert entry.runtime_data.store.desired == {"remote_airflow_m3h": 250}
    assert fake_gateway.holding_words[8002] == 250
    state = hass.states.get(_entity_id(hass, "number", "remote_airflow_m3h"))
    assert state is not None
    assert state.state == "250"
