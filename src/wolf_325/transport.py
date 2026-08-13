"""Serialized pymodbus transport, retries, and connection lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from pymodbus import FramerType
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

from .errors import CommunicationError, ConfigError, RemoteModbusError
from .types import TableName

LOGGER = logging.getLogger("wolf_325")


class TransportMixin:
    """Provide serialized request and reconnection behavior to the controller."""

    async def _request_read(self, table: TableName, address: int, count: int) -> Any:
        """Read a contiguous register range from the selected Modbus table."""
        method = (
            "read_input_registers" if table == "input" else "read_holding_registers"
        )
        return await self._request(method, address, count=count)

    async def _request(self, method: str, address: int, **kwargs: Any) -> Any:
        """Execute one serialized request with configured reconnect retries."""
        if self.config is None:
            await self.load_config()
        connection = self.config["connection"]
        attempts = int(connection["request_retries"]) + 1
        wire_address = address + int(connection["address_offset"])
        if wire_address < 0:
            raise ConfigError(f"address offset makes register {address} negative")
        async with self._io_lock:
            last_error: Exception | None = None
            for attempt in range(attempts):
                try:
                    await self._connect_locked()
                    call = getattr(self._client, method)
                    result = await call(
                        wire_address,
                        device_id=int(connection["device_id"]),
                        **kwargs,
                    )
                    if result.isError():
                        if isinstance(result, ExceptionResponse):
                            raise RemoteModbusError(
                                f"{method} address {address}: {result}"
                            )
                        raise ModbusException(f"{method} address {address}: {result}")
                    self._last_connection_error = None
                    return result
                except RemoteModbusError:
                    raise
                except asyncio.CancelledError:
                    raise
                except (ModbusException, OSError, TimeoutError, ConnectionError) as exc:
                    last_error = exc
                    self._last_connection_error = type(exc).__name__
                    self._close_client_locked()
                    if attempt + 1 < attempts:
                        await asyncio.sleep(min(0.25 * (2**attempt), 2.0))
            error_type = type(last_error).__name__ if last_error is not None else "unknown"
            raise CommunicationError(
                f"{method} register {address} failed after {attempts} "
                f"attempt(s) ({error_type})"
            ) from None

    async def _connect_locked(self) -> None:
        """Connect a new pymodbus client while the caller owns the I/O lock."""
        if self._client is not None and self._client.connected:
            return
        self._close_client_locked()
        connection = self.config["connection"]
        framer = (
            FramerType.SOCKET
            if connection["transport"] == "modbus_tcp"
            else FramerType.RTU
        )
        self._client = AsyncModbusTcpClient(
            str(connection["host"]),
            port=int(connection["port"]),
            framer=framer,
            timeout=float(connection["timeout_seconds"]),
            retries=int(connection["client_retries"]),
            reconnect_delay=float(connection["reconnect_delay_seconds"]),
            reconnect_delay_max=float(connection["reconnect_delay_max_seconds"]),
            name="wolf-cwl2-325",
        )
        connected = await self._client.connect()
        if not connected:
            self._close_client_locked()
            raise CommunicationError("could not connect to configured gateway")
        self._connection_generation += 1
        LOGGER.info(
            "connected to configured gateway (generation %s)",
            self._connection_generation,
        )

    def _close_client_locked(self) -> None:
        """Close and discard the current client while tolerating close failures."""
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
        self._client = None
