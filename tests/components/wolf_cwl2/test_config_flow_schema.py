"""Regression tests for frontend-safe WOLF CWL-2 config-flow schemas."""

from __future__ import annotations

import pytest
import voluptuous_serialize
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv

from custom_components.wolf_cwl2.config_schema import connection_schema
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


def test_connection_form_schema_is_frontend_serializable() -> None:
    """Serialize every initial connection field through Home Assistant's API path.

    Returns:
        None.
    """
    fields = voluptuous_serialize.convert(
        connection_schema(),
        custom_serializer=cv.custom_serializer,
    )

    assert [field["name"] for field in fields] == [
        "host",
        "port",
        "device_id",
        "transport",
        "address_offset",
    ]
    assert fields[0] == {
        "type": "string",
        "lengthMin": 1,
        "name": "host",
        "default": "",
        "required": True,
    }


async def test_connection_flow_normalizes_host_before_identity_probe(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Reject blank hosts and strip valid hosts before external device access.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={**CONNECTION, "host": "   "},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}
    assert fake_gateway.clients == []

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={**CONNECTION, "host": "  test-gateway  "},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "test-gateway"
    assert fake_gateway.clients[0].args[0] == "test-gateway"
