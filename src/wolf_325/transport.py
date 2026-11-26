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


def _safe_error_summary(exc: BaseException) -> str:
    """Describe a transport failure without exposing external exception text."""
    details = [type(exc).__name__]
    for attribute in ("errno", "winerror"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            details.append(f"{attribute}={value}")
    return " ".join(details)


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
                    LOGGER.debug(
                        "Modbus request succeeded: operation=%s address=%s "
                        "count=%s attempts=%d",
                        method,
                        address,
                        kwargs.get("count"),
                        attempt + 1,
                    )
                    return result
                except RemoteModbusError:
                    raise
                except asyncio.CancelledError:
                    raise
                except (
                    CommunicationError,
                    ModbusException,
                    OSError,
                    TimeoutError,
                    ConnectionError,
                ) as exc:
                    last_error = exc
                    self._last_connection_error = (
                        "connect_failed"
                        if isinstance(exc, CommunicationError)
                        else type(exc).__name__
                    )
                    error_summary = _safe_error_summary(exc)
                    LOGGER.debug(
                        "Modbus request attempt failed: operation=%s address=%s "
                        "count=%s attempt=%d/%d error=%s",
                        method,
                        address,
                        kwargs.get("count"),
                        attempt + 1,
                        attempts,
                        error_summary,
                    )
                    self._close_client_locked()
                    if attempt + 1 < attempts:
                        await asyncio.sleep(min(0.25 * (2**attempt), 2.0))
            error_type = (
                type(last_error).__name__ if last_error is not None else "unknown"
            )
            error_summary = (
                _safe_error_summary(last_error)
                if last_error is not None
                else "unknown"
            )
            LOGGER.warning(
                "Modbus request exhausted retries: operation=%s address=%s "
                "count=%s attempts=%d error=%s",
                method,
                address,
                kwargs.get("count"),
                attempts,
                error_summary,
            )
            if self._last_connection_error == "connect_failed":
                message = (
                    "could not connect to configured gateway after "
                    f"{attempts} attempt(s)"
                )
            else:
                message = (
                    f"{method} register {address} failed after {attempts} "
                    f"attempt(s) ({error_type})"
                )
            raise CommunicationError(message) from None

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
            self._last_connection_error = "connect_failed"
            self._close_client_locked()
            LOGGER.debug(
                "Modbus connection attempt rejected: transport=%s "
                "timeout_seconds=%s client_retries=%s",
                connection["transport"],
                connection["timeout_seconds"],
                connection["client_retries"],
            )
            raise CommunicationError("could not connect to configured gateway")
        self._last_connection_error = None
        self._connection_generation += 1
        LOGGER.info(
            "connected to configured gateway (generation %s)",
            self._connection_generation,
        )

    def _close_client_locked(self) -> None:
        """Close and discard the current client while tolerating close failures."""
        client = self._client
        if client is not None:
            LOGGER.debug(
                "closing Modbus client (was_connected=%s generation=%s)",
                bool(client.connected),
                self._connection_generation,
            )
            with contextlib.suppress(Exception):
                client.close()
        self._client = None
