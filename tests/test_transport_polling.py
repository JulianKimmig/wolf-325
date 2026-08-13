"""Failure-path tests for polling, writes, and optional-register handling."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pymodbus.pdu import ExceptionResponse

from wolf_325 import REGISTERS, WolfCWL2

from conftest import FakeClient, FakeResponse


async def test_poll_loop_and_reconcile_loop_exit_on_stop_event(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Both background loop types honor an already-signaled shutdown promptly."""
    instance, _ = controller
    instance._stop_event.set()
    await asyncio.wait_for(instance._poll_loop("fast", 0.01), timeout=1)
    await asyncio.wait_for(instance._reconcile_loop(), timeout=1)


async def test_poll_and_reconcile_loops_execute_one_cycle_before_shutdown(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Live background loops perform work after their interval and then stop cleanly."""
    instance, client = controller
    instance._stop_event.clear()
    polling = asyncio.create_task(instance._poll_loop("fast", 0.01))
    reconciling = asyncio.create_task(instance._reconcile_loop())
    assert instance.config is not None
    instance.config["polling"]["reconcile_interval_seconds"] = 0.01
    await asyncio.sleep(0.04)
    instance._stop_event.set()
    await asyncio.gather(polling, reconciling)
    assert any(table == "input" for table, *_ in client.reads)


async def test_poll_tier_tolerates_remote_exceptions_and_marks_values(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Protocol rejections mark affected blocks unavailable while polling continues."""
    instance, client = controller

    async def rejected(*_: Any, **__: Any) -> ExceptionResponse:
        """Reject every input block as an illegal appliance address."""
        return ExceptionResponse(4, 2)

    client.read_input_registers = rejected  # type: ignore[method-assign]
    await instance._poll_tier("fast")
    assert instance.get_state("active_function")["available"] is False
    assert "address 4020" in str(instance.get_state("active_function")["error"])


async def test_unverified_and_dangerous_writes_update_cache_without_readback(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Explicit no-verify and dangerous writes expose normalized cached results."""
    instance, client = controller
    assert await instance.set_setting(
        "bypass_mode", "open", persist=False, verify=False
    ) == "open"
    assert instance.get_state("bypass_mode")["available"] is True
    assert await instance.set_setting(
        "modbus_slave_address",
        21,
        persist=False,
        allow_dangerous=True,
    ) == 21
    assert (7991, 21, 20) in client.writes


async def test_low_level_write_guards_reject_invalid_categories(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Low-level write helpers retain read-only, one-shot, and dangerous guards."""
    instance, _ = controller
    with pytest.raises(Exception, match="read-only"):
        await instance._write_definition(
            REGISTERS["filter_status"],
            "clean",
            verify=False,
            allow_dangerous=False,
        )
    with pytest.raises(Exception, match="dedicated one-shot"):
        await instance._write_definition(
            REGISTERS["filter_reset_status"],
            "executed",
            verify=False,
            allow_dangerous=False,
        )
    with pytest.raises(Exception, match="requires allow_dangerous"):
        await instance._write_definition(
            REGISTERS["modbus_slave_address"],
            21,
            verify=False,
            allow_dangerous=False,
        )
    with pytest.raises(Exception, match="explicit confirmation"):
        await instance._write_raw(
            REGISTERS["modbus_slave_address"], 21, allow_dangerous=False
        )


async def test_optional_short_block_falls_back_to_individual_definitions(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A connected optional partial response isolates only its short definition."""
    instance, client = controller
    original_read = client.read_input_registers

    async def partially_supported(
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **kwargs: Any,
    ) -> FakeResponse:
        """Emulate the live UWA2-E block whose address 4503 has zero words."""
        if address == 4500 and count == 6:
            return FakeResponse([0, 0, 0])
        if address == 4503:
            return FakeResponse([])
        return await original_read(
            address, count=count, device_id=device_id, **kwargs
        )

    client.read_input_registers = partially_supported  # type: ignore[method-assign]
    await instance._poll_tier("static")
    assert instance.get_state("extension_software_version")["available"] is True
    assert instance.get_state("extension_hardware_version")["available"] is False
    assert "short response" in str(
        instance.get_state("extension_hardware_version")["error"]
    )
    assert instance.get_state("extension_device_type")["available"] is True


async def test_optional_short_definition_is_reported_unavailable(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A zero-word optional definition is unavailable without breaking the link."""
    instance, client = controller

    async def empty(*_: Any, **__: Any) -> FakeResponse:
        """Emulate the appliance's zero-byte optional-register response."""
        return FakeResponse([])

    client.read_input_registers = empty  # type: ignore[method-assign]
    assert await instance.refresh("extension_hardware_version") is None
    state = instance.get_state("extension_hardware_version")
    assert state["available"] is False
    assert "short response" in str(state["error"])
    assert instance.connected is True
