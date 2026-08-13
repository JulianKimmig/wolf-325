"""Deterministic external Modbus gateway fakes for Home Assistant tests."""

from __future__ import annotations

import asyncio
from typing import Any

class FakeResponse:
    """Represent one successful external Modbus read response."""

    def __init__(self, registers: list[int]) -> None:
        """Initialize response words.

        Args:
            registers: Wire words returned to the real client transport.
        """
        self.registers = registers

    def isError(self) -> bool:  # noqa: N802 - PyModbus compatibility
        """Report a successful protocol response.

        Returns:
            Always ``False`` for this external success fake.
        """
        return False


class FakeModbusClient:
    """Simulate one gateway connection while recording public wire activity."""

    def __init__(self, gateway: "FakeGateway", *args: Any, **kwargs: Any) -> None:
        """Initialize a client created by the real transport constructor.

        Args:
            gateway: Shared external fake state.
            *args: Positional PyModbus constructor arguments.
            **kwargs: Keyword PyModbus constructor arguments.
        """
        self.gateway = gateway
        self.args = args
        self.kwargs = kwargs
        self.connected = False

    async def connect(self) -> bool:
        """Connect or report the configured external failure.

        Returns:
            Whether the fake gateway accepts the connection.
        """
        self.connected = self.gateway.connects
        return self.connected

    async def read_input_registers(
        self,
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **_: Any,
    ) -> FakeResponse:
        """Return configured input words and record the request.

        Args:
            address: First wire register address.
            count: Requested contiguous word count.
            device_id: Downstream appliance unit identifier.
            **_: Unused PyModbus compatibility arguments.

        Returns:
            Successful response containing configured words.
        """
        await self.gateway.wait_if_blocked(device_id)
        if self.gateway.fails_reads:
            raise OSError(self.gateway.read_failure_message)
        self.gateway.reads.append((address, count, device_id))
        return FakeResponse(
            [self.gateway.input_words.get(address + offset, 0) for offset in range(count)]
        )

    async def read_holding_registers(
        self,
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **_: Any,
    ) -> FakeResponse:
        """Return configured holding words and record the request.

        Args:
            address: First wire register address.
            count: Requested contiguous word count.
            device_id: Downstream appliance unit identifier.
            **_: Unused PyModbus compatibility arguments.

        Returns:
            Successful response containing configured words.
        """
        await self.gateway.wait_if_blocked(device_id)
        if self.gateway.fails_reads:
            raise OSError(self.gateway.read_failure_message)
        self.gateway.holding_reads.append((address, count, device_id))
        return FakeResponse(
            [
                self.gateway.holding_words.get(address + offset, 0)
                for offset in range(count)
            ]
        )

    async def write_register(
        self,
        address: int,
        *,
        value: int,
        device_id: int = 1,
        **_: Any,
    ) -> FakeResponse:
        """Store one holding word and record the external write.

        Args:
            address: Wire register address to mutate.
            value: Encoded unsigned 16-bit register word.
            device_id: Downstream appliance unit identifier.
            **_: Unused PyModbus compatibility arguments.

        Returns:
            Successful external protocol response.

        Raises:
            OSError: If this address is configured to simulate transport loss.
        """
        self.gateway.write_attempts.append((address, value, device_id))
        if address in self.gateway.write_failure_addresses:
            raise OSError("simulated gateway write failure")
        self.gateway.writes.append((address, value, device_id))
        written_word = (
            1 if value == 1 else 0
        ) if address == 8003 else value
        self.gateway.holding_words[address] = self.gateway.write_readback_words.get(
            address, written_word
        )
        return FakeResponse([])

    def close(self) -> None:
        """Close the simulated external connection.

        Returns:
            None.
        """
        self.connected = False
        self.gateway.closes += 1


class FakeGateway:
    """Configure identity and connection outcomes for constructed clients."""

    def __init__(self) -> None:
        """Initialize one reachable appliance with a valid serial identity."""
        self.connects = True
        self.fails_reads = False
        self.read_failure_message = "simulated gateway read failure"
        self.blocked_device_id: int | None = None
        self.block_started = asyncio.Event()
        self.release_block = asyncio.Event()
        self.serial = "123456789012"
        self.appliance_type = 325
        self.input_words: dict[int, int] = {}
        self.holding_words: dict[int, int] = {}
        self.reads: list[tuple[int, int, int]] = []
        self.holding_reads: list[tuple[int, int, int]] = []
        self.write_attempts: list[tuple[int, int, int]] = []
        self.writes: list[tuple[int, int, int]] = []
        self.write_failure_addresses: set[int] = set()
        self.write_readback_words: dict[int, int] = {}
        self.clients: list[FakeModbusClient] = []
        self.closes = 0
        self.apply_identity()

    async def wait_if_blocked(self, device_id: int) -> None:
        """Pause requests for one selected device without blocking other entries.

        Args:
            device_id: Downstream appliance identifier for the current request.

        Returns:
            None immediately or after the test releases the selected device.
        """
        if device_id != self.blocked_device_id:
            return
        self.block_started.set()
        await self.release_block.wait()

    def apply_identity(self) -> None:
        """Encode configured identity values into external input words.

        Returns:
            None.
        """
        serial_words = _encode_serial_words(self.serial)
        for offset, word in enumerate(serial_words):
            self.input_words[4010 + offset] = word
        self.input_words[4004] = self.appliance_type

    def construct_client(self, *args: Any, **kwargs: Any) -> FakeModbusClient:
        """Construct and retain one fake PyModbus client.

        Args:
            *args: Positional PyModbus constructor arguments.
            **kwargs: Keyword PyModbus constructor arguments.

        Returns:
            New fake client connected to this gateway state.
        """
        client = FakeModbusClient(self, *args, **kwargs)
        self.clients.append(client)
        return client


def _encode_serial_words(serial: str) -> list[int]:
    """Encode a 12-digit external serial as three packed BCD words.

    Args:
        serial: Twelve decimal digits presented by the simulated appliance.

    Returns:
        Three raw input-register words consumed by the real client decoder.
    """
    if len(serial) != 12 or not serial.isdigit():
        raise ValueError("fake serial must contain exactly 12 decimal digits")
    return [int(serial[index : index + 4], 16) for index in range(0, 12, 4)]
