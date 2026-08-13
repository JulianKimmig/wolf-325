"""Guarded filter and appliance reset action tests."""

from __future__ import annotations

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(authority: str, *, allow_appliance_reset: bool = False) -> MockConfigEntry:
    """Build one entry for guarded reset tests.

    Args:
        authority: Canonical runtime authority mode.
        allow_appliance_reset: Explicit dangerous-action option.

    Returns:
        Detached serial-backed config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="Reset ventilation",
        unique_id="123456789012",
        data=CONNECTION,
        options={
            **DEFAULT_OPTIONS,
            "authority": authority,
            "allow_appliance_reset": allow_appliance_reset,
        },
    )


async def test_filter_reset_requires_phrase_and_nonmonitor_authority(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject failed filter gates and dispatch one accepted public action.

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
    with pytest.raises(ServiceValidationError, match="temporary or persistent"):
        await hass.services.async_call(
            DOMAIN,
            "reset_filter",
            {
                "config_entry_id": entry.entry_id,
                "confirmation": "EXECUTE ACTION",
            },
            blocking=True,
            return_response=True,
        )
    assert fake_gateway.writes == []

    await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "authority": "temporary"}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    with pytest.raises(ServiceValidationError, match="EXECUTE ACTION"):
        await hass.services.async_call(
            DOMAIN,
            "reset_filter",
            {"config_entry_id": entry.entry_id, "confirmation": "yes"},
            blocking=True,
            return_response=True,
        )
    response = await hass.services.async_call(
        DOMAIN,
        "reset_filter",
        {"config_entry_id": entry.entry_id, "confirmation": "EXECUTE ACTION"},
        blocking=True,
        return_response=True,
    )
    assert response["status"] in {"executed", "command_sent"}
    assert fake_gateway.writes == [(8010, 1, 20)]
    assert entry.runtime_data.store.revision == revision + 1
    assert entry.runtime_data.store.desired == {}


async def test_appliance_reset_requires_admin_opt_in_phrase_and_live_identity(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Enforce every appliance reset gate before one dispatch-only write.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    user = await hass.auth.async_create_user("Reset administrator")
    assert user.is_admin
    context = Context(user_id=user.id)
    entry = _entry("temporary")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    revision = entry.runtime_data.store.revision

    with pytest.raises(ServiceValidationError, match="enabled"):
        await hass.services.async_call(
            DOMAIN,
            "reset_appliance",
            {"config_entry_id": entry.entry_id, "confirmation": "RESET APPLIANCE"},
            blocking=True,
            context=context,
            return_response=True,
        )
    await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "allow_appliance_reset": True}
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    with pytest.raises(ServiceValidationError, match="RESET APPLIANCE"):
        await hass.services.async_call(
            DOMAIN,
            "reset_appliance",
            {"config_entry_id": entry.entry_id, "confirmation": "reset"},
            blocking=True,
            context=context,
            return_response=True,
        )
    with pytest.raises(ServiceValidationError, match="administrator"):
        await hass.services.async_call(
            DOMAIN,
            "reset_appliance",
            {"config_entry_id": entry.entry_id, "confirmation": "RESET APPLIANCE"},
            blocking=True,
            return_response=True,
        )
    response = await hass.services.async_call(
        DOMAIN,
        "reset_appliance",
        {"config_entry_id": entry.entry_id, "confirmation": "RESET APPLIANCE"},
        blocking=True,
        context=context,
        return_response=True,
    )
    assert response == {"status": "command_sent"}
    assert fake_gateway.writes == [(8011, 1, 20)]
    assert not entry.runtime_data.controller.connected
    assert not entry.runtime_data.coordinator.last_update_success
    assert entry.runtime_data.store.revision == revision
    assert entry.runtime_data.store.desired == {}
    assert not hass.services.has_service(DOMAIN, "write_register")

    await entry.runtime_data.coordinator.async_refresh()
    assert entry.runtime_data.controller.connected


async def test_reset_rechecks_identity_and_translates_gateway_failure(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject a changed or unreadable target without dispatching a reset.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("temporary")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    revision = entry.runtime_data.store.revision

    fake_gateway.serial = "999999999999"
    fake_gateway.apply_identity()
    with pytest.raises(HomeAssistantError, match="identity no longer matches"):
        await hass.services.async_call(
            DOMAIN,
            "reset_filter",
            {"config_entry_id": entry.entry_id, "confirmation": "EXECUTE ACTION"},
            blocking=True,
            return_response=True,
        )

    fake_gateway.serial = "123456789012"
    fake_gateway.apply_identity()
    fake_gateway.fails_reads = True
    with pytest.raises(HomeAssistantError, match="did not confirm"):
        await hass.services.async_call(
            DOMAIN,
            "reset_filter",
            {"config_entry_id": entry.entry_id, "confirmation": "EXECUTE ACTION"},
            blocking=True,
            return_response=True,
        )
    assert fake_gateway.writes == []
    assert entry.runtime_data.store.revision == revision
    assert entry.runtime_data.store.desired == {}
