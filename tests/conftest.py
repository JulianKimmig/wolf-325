"""Shared pytest fixtures and a deterministic external Modbus simulator."""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from wolf_325 import DEFAULT_CONFIG, WolfCWL2


class FakeResponse:
    """Represent a successful or failed response from an external gateway."""

    def __init__(
        self,
        registers: list[int] | None = None,
        *,
        error: bool = False,
    ) -> None:
        """Initialize a response.

        Args:
            registers: Register words returned by a read operation.
            error: Whether the simulated protocol operation failed.
        """
        self.registers = [] if registers is None else registers
        self._error = error

    def isError(self) -> bool:  # noqa: N802 - pymodbus compatibility
        """Return whether pymodbus should treat the response as an error."""
        return self._error


class FakeClient:
    """Simulate the network gateway while retaining all observable I/O."""

    def __init__(self) -> None:
        """Initialize connected register stores and operation history."""
        self.connected = True
        self.input: dict[int, int] = {}
        self.holding: dict[int, int] = {}
        self.reads: list[tuple[str, int, int, int]] = []
        self.writes: list[tuple[int, int, int]] = []
        self.fail_reads = False
        self.fail_writes = False

    async def connect(self) -> bool:
        """Mark the simulated external gateway connected and report success."""
        self.connected = True
        return True

    async def read_input_registers(
        self,
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **_: Any,
    ) -> FakeResponse:
        """Read a contiguous simulated input-register range."""
        self.reads.append(("input", address, count, device_id))
        return FakeResponse(
            [self.input.get(address + offset, 0) for offset in range(count)],
            error=self.fail_reads,
        )

    async def read_holding_registers(
        self,
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **_: Any,
    ) -> FakeResponse:
        """Read a contiguous simulated holding-register range."""
        self.reads.append(("holding", address, count, device_id))
        return FakeResponse(
            [self.holding.get(address + offset, 0) for offset in range(count)],
            error=self.fail_reads,
        )

    async def write_register(
        self,
        address: int,
        value: int,
        *,
        device_id: int = 1,
        **_: Any,
    ) -> FakeResponse:
        """Write a word and emulate the standby command's asymmetric state."""
        self.writes.append((address, value, device_id))
        if not self.fail_writes:
            self.holding[address] = (
                1 if value == 1 else 0
            ) if address == 8003 else value
        return FakeResponse(error=self.fail_writes)

    def close(self) -> None:
        """Mark the simulated external gateway disconnected."""
        self.connected = False


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """Create a complete fast-running configuration in a temporary directory."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["connection"]["host"] = "fake-gateway"
    config["connection"]["request_retries"] = 0
    config["persistence"]["verify_delay_seconds"] = 0
    config["state_file"] = "state.json"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    (tmp_path / "profiles").mkdir()
    return path


@pytest.fixture
async def controller(config_path: Path) -> Iterator[tuple[WolfCWL2, FakeClient]]:
    """Provide a loaded controller connected to the external Modbus simulator."""
    instance = WolfCWL2(config_path)
    await instance.load_config()
    client = FakeClient()
    instance._client = client
    try:
        yield instance, client
    finally:
        await instance.stop()
