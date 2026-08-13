"""Tests for the read-only Home Assistant appliance identity probe."""

from __future__ import annotations

import pytest

from custom_components.wolf_cwl2.probe import (
    CannotConnect,
    InvalidIdentity,
    async_probe_device,
)

from .fakes import FakeGateway

CONNECTION = {
    "host": "test-gateway",
    "port": 502,
    "device_id": 20,
    "transport": "modbus_tcp",
    "address_offset": 0,
}


async def test_probe_uses_real_read_only_client_and_always_closes(
    fake_gateway: FakeGateway,
) -> None:
    """Read identity through the public controller without writes or background work.

    Args:
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    identity = await async_probe_device(CONNECTION)

    assert identity.serial_number == "123456789012"
    assert identity.appliance_type == 325
    assert fake_gateway.reads == [(4010, 3, 20), (4004, 1, 20)]
    assert fake_gateway.closes == 1
    assert all(not client.connected for client in fake_gateway.clients)


async def test_probe_maps_connection_failure_and_closes(
    fake_gateway: FakeGateway,
) -> None:
    """Map an unreachable external gateway to a flow-safe connection error.

    Args:
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.connects = False

    with pytest.raises(CannotConnect):
        await async_probe_device(CONNECTION)
    assert fake_gateway.closes == 1


async def test_probe_rejects_zero_serial_without_endpoint_fallback(
    fake_gateway: FakeGateway,
) -> None:
    """Reject an unverified serial instead of constructing endpoint identity.

    Args:
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.serial = "000000000000"
    fake_gateway.apply_identity()

    with pytest.raises(InvalidIdentity):
        await async_probe_device(CONNECTION)
    assert fake_gateway.closes == 1
