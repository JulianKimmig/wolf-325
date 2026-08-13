"""Tests for WOLF CWL-2 configuration, reconfigure, and options flows."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

CONNECTION = {
    "host": "test-gateway",
    "port": 502,
    "device_id": 20,
    "transport": "modbus_tcp",
    "address_offset": 0,
}
DEFAULT_OPTIONS = {
    "authority": "monitor_only",
    "fast_interval_seconds": 5,
    "slow_interval_seconds": 60,
    "static_interval_seconds": 300,
    "reconcile_interval_seconds": 30,
    "read_holding_registers": True,
    "read_extension_registers": True,
    "allow_appliance_reset": False,
}


async def _start_user_flow(hass: HomeAssistant) -> dict[str, object]:
    """Start the public user flow and return its form result.

    Args:
        hass: Home Assistant test instance.

    Returns:
        Initial flow result mapping.
    """
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )


async def _submit_connection(
    hass: HomeAssistant,
    flow_id: str,
    connection: dict[str, object] | None = None,
) -> dict[str, object]:
    """Submit one connection mapping through the public flow manager.

    Args:
        hass: Home Assistant test instance.
        flow_id: Active flow identifier.
        connection: Optional replacement for the default fake endpoint.

    Returns:
        Result returned by Home Assistant flow handling.
    """
    return await hass.config_entries.flow.async_configure(
        flow_id,
        user_input=dict(connection or CONNECTION),
    )


async def test_user_flow_creates_serial_backed_entry(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Create one entry only after a successful read-only identity probe.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await _submit_connection(hass, result["flow_id"])
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "WOLF CWL-2 123456789012"
    assert result["data"] == CONNECTION
    assert result["options"] == DEFAULT_OPTIONS
    entry = result["result"]
    assert entry.unique_id == "123456789012"
    assert fake_gateway.closes == 1


async def test_user_flow_reports_connection_and_identity_errors(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Keep the form open with actionable probe error keys.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.connects = False
    result = await _start_user_flow(hass)
    result = await _submit_connection(hass, result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    fake_gateway.connects = True
    fake_gateway.serial = "000000000000"
    fake_gateway.apply_identity()
    result = await _submit_connection(hass, result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_identity"}


async def test_duplicate_serial_aborts_but_distinct_serial_configures(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Support multiple appliances while rejecting duplicate serial identity.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    first = await _start_user_flow(hass)
    assert (await _submit_connection(hass, first["flow_id"]))["type"] is FlowResultType.CREATE_ENTRY

    duplicate = await _start_user_flow(hass)
    duplicate = await _submit_connection(hass, duplicate["flow_id"])
    assert duplicate["type"] is FlowResultType.ABORT
    assert duplicate["reason"] == "already_configured"

    fake_gateway.serial = "999999999999"
    fake_gateway.apply_identity()
    second = await _start_user_flow(hass)
    second = await _submit_connection(
        hass,
        second["flow_id"],
        {**CONNECTION, "device_id": 21},
    )
    assert second["type"] is FlowResultType.CREATE_ENTRY
    assert second["result"].unique_id == "999999999999"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


async def test_reconfigure_updates_only_matching_serial(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Update an endpoint only when its live serial still matches the entry.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WOLF CWL-2 123456789012",
        unique_id="123456789012",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    updated = {**CONNECTION, "host": "replacement-gateway"}
    result = await _submit_connection(hass, result["flow_id"], updated)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == updated

    mismatch = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    fake_gateway.serial = "999999999999"
    fake_gateway.apply_identity()
    mismatch = await _submit_connection(hass, mismatch["flow_id"], CONNECTION)
    assert mismatch["type"] is FlowResultType.ABORT
    assert mismatch["reason"] == "reconfigure_mismatch"
    assert entry.data == updated


async def test_options_validate_modes_intervals_and_reload_once(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject unsafe cadence and reload one loaded entry for valid policy.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.
        monkeypatch: Pytest helper for the external HA reload boundary.

    Returns:
        None.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WOLF CWL-2 123456789012",
        unique_id="123456789012",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    reload_entry = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    invalid = {**DEFAULT_OPTIONS, "fast_interval_seconds": 4}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=invalid
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_interval"}

    valid = {**DEFAULT_OPTIONS, "authority": "persistent"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=valid
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == valid
    reload_entry.assert_awaited_once_with(entry.entry_id)


@pytest.mark.parametrize("authority", ["monitor_only", "temporary", "persistent"])
@pytest.mark.parametrize("interval", [5, 6])
async def test_options_accept_every_mode_at_and_above_interval_floor(
    hass: HomeAssistant,
    authority: str,
    interval: int,
) -> None:
    """Accept all authority modes at the lower bound and immediately above it.

    Args:
        hass: Home Assistant test instance.
        authority: Supported per-entry authority mode.
        interval: Safe fast interval at or above the five-second floor.

    Returns:
        None.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Options {authority} {interval}",
        unique_id=f"{interval:02d}{len(authority):010d}",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    selected = {
        **DEFAULT_OPTIONS,
        "authority": authority,
        "fast_interval_seconds": interval,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=selected
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == selected
