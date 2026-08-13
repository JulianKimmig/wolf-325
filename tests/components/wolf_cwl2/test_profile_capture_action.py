"""Home Assistant profile preview and exact desired-state capture tests."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(authority: str) -> MockConfigEntry:
    """Build one entry for profile-capture service tests.

    Args:
        authority: Canonical authority mode.

    Returns:
        Detached serial-backed config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Capture ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={**DEFAULT_OPTIONS, "authority": authority},
    )


def _entity_id(hass: HomeAssistant, domain: str, suffix: str) -> str:
    """Resolve a stable integration entity by unique-ID suffix.

    Args:
        hass: Home Assistant instance owning the registry.
        domain: Entity platform domain.
        suffix: Integration unique-ID suffix.

    Returns:
        Registered entity ID.
    """
    entity_id = er.async_get(hass).async_get_entity_id(
        domain, DOMAIN, f"123456789012_{suffix}"
    )
    assert entity_id is not None
    return entity_id


async def test_preview_and_save_capture_exact_persistent_desired_delta(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Save a derived profile without any capture-time Modbus operation.

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
        {"entity_id": _entity_id(hass, "select", "profile"), "option": "night"},
        blocking=True,
    )
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": _entity_id(hass, "number", "remote_airflow_m3h"),
            "value": 180,
        },
        blocking=True,
    )
    store = entry.runtime_data.store
    revision = store.revision
    reads_before = len(fake_gateway.reads) + len(fake_gateway.holding_reads)
    writes_before = len(fake_gateway.writes)

    preview = await hass.services.async_call(
        DOMAIN,
        "preview_profile_capture",
        {"config_entry_id": entry.entry_id},
        blocking=True,
        return_response=True,
    )
    assert preview == {
        "base": "night",
        "settings": {"remote_airflow_m3h": 180},
        "unset": [],
        "replace": False,
        "has_changes": True,
        "revision": revision,
    }
    saved = await hass.services.async_call(
        DOMAIN,
        "save_profile",
        {
            "config_entry_id": entry.entry_id,
            "name": "quiet-with-airflow",
            "description": "Night plus direct airflow ownership",
            "expected_revision": revision,
        },
        blocking=True,
        return_response=True,
    )
    assert saved["name"] == "quiet-with-airflow"
    assert saved["base"] == "night"
    assert saved["settings"] == {"remote_airflow_m3h": 180}
    assert saved["revision"] == revision + 1
    assert len(fake_gateway.reads) + len(fake_gateway.holding_reads) == reads_before
    assert len(fake_gateway.writes) == writes_before
    assert store.desired["remote_airflow_m3h"] == 180
    assert store.last_profile == "night"
    assert store.last_applied_profile == "night"
    profile_state = hass.states.get(_entity_id(hass, "select", "profile"))
    assert profile_state is not None
    assert "quiet-with-airflow" in profile_state.attributes["options"]
    assert profile_state.state == "night"


async def test_capture_rejects_nonpersistent_and_stale_revision_without_mutation(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject temporary source and optimistic-concurrency races safely.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    temporary = _entry("temporary")
    temporary.add_to_hass(hass)
    assert await hass.config_entries.async_setup(temporary.entry_id)
    with pytest.raises(ServiceValidationError, match="persistent"):
        await hass.services.async_call(
            DOMAIN,
            "save_profile",
            {"config_entry_id": temporary.entry_id, "name": "invalid-source"},
            blocking=True,
            return_response=True,
        )

    await hass.config_entries.async_unload(temporary.entry_id)
    hass.config_entries.async_update_entry(
        temporary,
        options={**temporary.options, "authority": "persistent"},
    )
    persistent = temporary
    assert await hass.config_entries.async_setup(persistent.entry_id)
    revision = persistent.runtime_data.store.revision
    with pytest.raises(ServiceValidationError, match="changed"):
        await hass.services.async_call(
            DOMAIN,
            "save_profile",
            {
                "config_entry_id": persistent.entry_id,
                "name": "stale",
                "expected_revision": revision - 1,
            },
            blocking=True,
            return_response=True,
        )
    assert persistent.runtime_data.store.revision == revision
