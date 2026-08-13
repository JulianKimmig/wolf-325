"""Failure-path tests for the external Modbus transport boundary."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from pymodbus import FramerType
from pymodbus.pdu import ExceptionResponse

from wolf_325 import (
    CommunicationError,
    ConfigError,
    REGISTERS,
    RemoteModbusError,
    WolfCWL2,
)
from wolf_325.register import ReadBlock

from conftest import FakeClient, FakeResponse


class ClientFactory:
    """Record pymodbus constructor options and return a supplied fake client."""

    def __init__(self, client: FakeClient, *, connect_result: bool = True) -> None:
        """Initialize a configurable fake external client factory."""
        self.client = client
        self.connect_result = connect_result
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> FakeClient:
        """Return the fake client after recording connection construction."""
        self.calls.append((args, kwargs))

        async def connect() -> bool:
            """Return the configured external connection result."""
            self.client.connected = self.connect_result
            return self.connect_result

        self.client.connect = connect  # type: ignore[method-assign]
        self.client.connected = False
        return self.client


async def test_connect_constructs_modbus_client_from_configuration(
    config_path: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Transport maps host, port, framing, timeout, and retry settings exactly."""
    import wolf_325.transport as transport_module

    instance = WolfCWL2(config_path)
    caplog.set_level(logging.INFO, logger="wolf_325")
    await instance.load_config()
    client = FakeClient()
    factory = ClientFactory(client)
    monkeypatch.setattr(transport_module, "AsyncModbusTcpClient", factory)
    await instance.refresh("filter_status")
    args, kwargs = factory.calls[0]
    assert args == ("fake-gateway",)
    assert kwargs["port"] == 502
    assert kwargs["framer"] == FramerType.SOCKET
    assert instance.snapshot()["connection_generation"] == 1
    assert "fake-gateway" not in caplog.text
    await instance.stop()


async def test_connect_uses_rtu_framer_and_reports_connection_refusal(
    config_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RTU-over-TCP selects RTU framing and false connect results fail clearly."""
    import wolf_325.transport as transport_module

    instance = WolfCWL2(config_path)
    await instance.load_config()
    assert instance.config is not None
    instance.config["connection"]["transport"] = "rtu_over_tcp"
    factory = ClientFactory(FakeClient(), connect_result=False)
    monkeypatch.setattr(transport_module, "AsyncModbusTcpClient", factory)
    with pytest.raises(CommunicationError, match="configured gateway") as failure:
        await instance.refresh("filter_status")
    assert "fake-gateway" not in str(failure.value)
    assert factory.calls[0][1]["framer"] == FramerType.RTU


async def test_negative_wire_address_fails_before_external_io(config_path: Any) -> None:
    """Address offsets that produce a negative wire address fail as configuration."""
    instance = WolfCWL2(config_path)
    await instance.load_config()
    assert instance.config is not None
    instance.config["connection"]["address_offset"] = -1
    with pytest.raises(ConfigError, match="negative"):
        await instance._request("read_input_registers", 0, count=1)


async def test_protocol_exception_is_remote_error_without_disconnect(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A Modbus exception response remains distinct from a broken TCP transport."""
    instance, client = controller

    async def rejected(*_: Any, **__: Any) -> ExceptionResponse:
        """Return a real pymodbus illegal-address response."""
        return ExceptionResponse(4, 2)

    client.read_input_registers = rejected  # type: ignore[method-assign]
    with pytest.raises(RemoteModbusError):
        await instance.refresh("filter_status")
    assert instance.connected is True


async def test_transport_failure_does_not_chain_sensitive_gateway_exception(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Keep raw external exception text out of host-visible traceback chains.

    Args:
        controller: Real controller plus its external gateway fake.

    Returns:
        None.
    """
    instance, client = controller
    sentinel = "sensitive external gateway exception"

    async def failed(*_: Any, **__: Any) -> FakeResponse:
        """Raise one external exception containing protected text."""
        raise OSError(sentinel)

    client.read_input_registers = failed  # type: ignore[method-assign]
    with pytest.raises(CommunicationError) as failure:
        await instance.refresh("filter_status")
    assert sentinel not in str(failure.value)
    assert failure.value.__cause__ is None


async def test_short_read_response_is_rejected(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Truncated external block and definition responses raise communication errors."""
    instance, client = controller

    async def short(*_: Any, **__: Any) -> FakeResponse:
        """Return no words for every simulated external read."""
        return FakeResponse([])

    client.read_input_registers = short  # type: ignore[method-assign]
    with pytest.raises(CommunicationError, match="short response reading"):
        await instance.refresh("serial_number")
    with pytest.raises(CommunicationError, match="short response for"):
        await instance._read_block(ReadBlock("input", "fast", 4020, 5))


async def test_decode_failure_is_cached_as_unavailable(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Unexpected decoder failure becomes value-level state rather than loop failure."""
    instance, _ = controller
    changed = await instance._update_value(REGISTERS["serial_number"], [1])
    state = instance.get_state("serial_number")
    assert changed is True
    assert state["available"] is False
    assert str(state["error"]).startswith("decode error")
