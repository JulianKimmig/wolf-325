"""Home Assistant state and registry tests for the complete read surface."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN
from custom_components.wolf_cwl2.entity_catalogue import ENTITY_SPECS

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry() -> MockConfigEntry:
    """Build one fully configured serial-backed entry.

    Returns:
        Detached Home Assistant config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Upstairs ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )


async def test_complete_sensor_surface_has_stable_registry_and_device_identity(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Create every sensor disposition with curated registry defaults.

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
    entries = [
        item
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
        if item.domain == "sensor"
    ]
    expected = {
        key: spec for key, spec in ENTITY_SPECS.items() if spec.platform == "sensor"
    }
    assert len(entries) == len(expected) == 83
    assert {item.unique_id for item in entries} == {
        f"123456789012_{key}" for key in expected
    }
    for item in entries:
        key = item.unique_id.removeprefix("123456789012_")
        assert (item.disabled_by is None) is expected[key].enabled_default

    devices = dr.async_entries_for_config_entry(
        dr.async_get(hass), entry.entry_id
    )
    assert len(devices) == 1
    device = next(iter(devices))
    assert device.identifiers == {(DOMAIN, "123456789012")}
    assert device.serial_number == "123456789012"
    assert device.name == "Upstairs ventilation"


async def test_sensor_state_is_confirmed_recorder_safe_and_unknown_enum_visible(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Publish canonical cached values without volatile attributes.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.input_words[4020] = 99
    fake_gateway.input_words[4032] = 171
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    airflow_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "123456789012_supply_airflow_actual_m3h"
    )
    function_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "123456789012_active_function"
    )
    assert airflow_id is not None
    assert function_id is not None
    airflow = hass.states.get(airflow_id)
    function = hass.states.get(function_id)
    assert airflow is not None
    assert function is not None
    assert airflow.state == "171"
    assert airflow.attributes["unit_of_measurement"] == "m³/h"
    assert airflow.attributes["device_class"] == "volume_flow_rate"
    assert airflow.attributes["state_class"] == "measurement"
    assert function.state == "unknown_99"
    forbidden = {"raw", "updated_at", "error", "desired", "last_profile"}
    assert forbidden.isdisjoint(airflow.attributes)
    assert forbidden.isdisjoint(function.attributes)


async def test_advanced_sensor_is_registered_but_not_loaded_by_default(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Keep diagnostics discoverable without creating default Recorder state.

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
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "123456789012_modbus_slave_address"
    )
    assert entity_id is not None
    assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None
