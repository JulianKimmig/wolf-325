"""Polling loops, register decoding, cache updates, and update distribution."""

from __future__ import annotations

import asyncio
import contextlib
import copy
import inspect
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from .catalogue import READ_BLOCKS, REGISTER_LIST
from .config import atomic_json_write
from .errors import CommunicationError, RemoteModbusError
from .register import ReadBlock, RegisterDef
from .state import ValueState
from .types import PollTier

LOGGER = logging.getLogger("wolf_325")


class PollingMixin:
    """Provide tiered polling and cached update behavior to the controller."""

    async def _poll_loop(self, tier: PollTier, interval: float) -> None:
        """Poll one tier repeatedly until shutdown while isolating failures."""
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                    break
                except TimeoutError:
                    pass
                try:
                    await self._poll_tier(tier)
                except CommunicationError as exc:
                    LOGGER.warning("%s poll failed: %s", tier, exc)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("unexpected failure in %s poll loop", tier)

    async def _reconcile_loop(self) -> None:
        """Periodically restore reconnect state and enforce desired values."""
        interval = float(self.config["polling"]["reconcile_interval_seconds"])
        persistence = self.config["persistence"]
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                    break
                except TimeoutError:
                    pass
                force = bool(persistence["restore_on_reconnect"]) and (
                    self._connection_generation != self._last_restored_generation
                )
                if force or bool(persistence["enforce_desired_state"]):
                    result = await self.apply_desired(force=force, raise_on_error=False)
                    if result["errors"]:
                        LOGGER.warning(
                            "desired-state reconcile incomplete: %s", result["errors"]
                        )
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("unexpected failure in reconcile loop")

    async def _poll_tier(self, tier: PollTier) -> None:
        """Read every enabled contiguous block for one polling tier."""
        if self.config is None:
            await self.load_config()
        changed = False
        for block in (item for item in READ_BLOCKS if item.tier == tier):
            if block.table == "holding" and not self.config["polling"]["read_holding_registers"]:
                continue
            if block.extension_only and not self.config["polling"]["read_extension_registers"]:
                continue
            try:
                changed = await self._read_block(block) or changed
            except RemoteModbusError as exc:
                await self._mark_block_unavailable(block, str(exc))
                if not block.optional:
                    LOGGER.warning(
                        "Modbus rejected required block %s %d..%d: %s",
                        block.table,
                        block.start,
                        block.start + block.count - 1,
                        exc,
                    )
            except CommunicationError:
                if block.optional and self.connected:
                    changed = (
                        await self._read_optional_definitions(block) or changed
                    )
                    continue
                await self._mark_block_unavailable(block, "connection unavailable")
                raise
        self._last_poll_at[tier] = datetime.now(UTC).isoformat()
        if changed:
            await self._write_state_file()

    async def _read_block(self, block: ReadBlock) -> bool:
        """Read and decode all definitions contained by a contiguous block."""
        response = await self._request_read(block.table, block.start, block.count)
        words = list(response.registers)
        if len(words) < block.count:
            raise CommunicationError(
                f"short response for {block.table} {block.start}: "
                f"expected {block.count}, got {len(words)}"
            )
        changed = False
        block_end = block.start + block.count
        for register in REGISTER_LIST:
            if register.table != block.table or register.poll != block.tier:
                continue
            if block.start <= register.address and register.address + register.count <= block_end:
                offset = register.address - block.start
                changed = await self._update_value(
                    register, words[offset : offset + register.count]
                ) or changed
        return changed

    async def _read_optional_definitions(self, block: ReadBlock) -> bool:
        """Recover a connected partial optional block through individual reads."""
        block_end = block.start + block.count
        definitions = [
            register
            for register in REGISTER_LIST
            if register.table == block.table
            and register.poll == block.tier
            and block.start <= register.address
            and register.address + register.count <= block_end
        ]
        changed = False
        for register in definitions:
            try:
                await self._read_definition(register)
                changed = True
            except (RemoteModbusError, CommunicationError) as exc:
                if not self.connected:
                    raise
                definition_block = ReadBlock(
                    register.table,
                    register.poll,
                    register.address,
                    register.count,
                    optional=True,
                )
                await self._mark_block_unavailable(definition_block, str(exc))
                changed = True
        return changed

    async def _read_definition(self, register: RegisterDef) -> ValueState:
        """Read and cache one logical definition independently of its poll block."""
        response = await self._request_read(register.table, register.address, register.count)
        words = list(response.registers)
        if len(words) < register.count:
            error = f"short response reading {register.key}"
            if register.optional and self.connected:
                await self._mark_block_unavailable(
                    ReadBlock(
                        register.table,
                        register.poll,
                        register.address,
                        register.count,
                        optional=True,
                    ),
                    error,
                )
                return self._values[register.key]
            raise CommunicationError(error)
        await self._update_value(register, words[: register.count])
        return self._values[register.key]

    async def _update_value(self, register: RegisterDef, words: Sequence[int]) -> bool:
        """Decode words, update cached availability, and emit a changed state."""
        now = datetime.now(UTC).isoformat()
        try:
            value = register.decode(words)
            error = None
            available = True
        except Exception as exc:
            value = None
            error = f"decode error: {exc}"
            available = False
        raw = register.raw_json(words)
        state = self._values[register.key]
        changed = (
            state.value != value
            or state.raw != raw
            or state.available != available
            or state.error != error
        )
        state.value = value
        state.raw = raw
        state.available = available
        state.error = error
        state.updated_at = now
        if changed:
            await self._emit_update(state)
        return changed

    async def _mark_block_unavailable(self, block: ReadBlock, error: str) -> None:
        """Mark all definitions intersecting a failed block unavailable."""
        now = datetime.now(UTC).isoformat()
        end = block.start + block.count
        for register in REGISTER_LIST:
            if register.table == block.table and block.start <= register.address < end:
                state = self._values[register.key]
                changed = state.available or state.error != error
                state.available = False
                state.error = error
                state.updated_at = now
                if changed:
                    await self._emit_update(state)

    async def _emit_update(self, state: ValueState) -> None:
        """Deliver an isolated state change to queues and sync/async callbacks."""
        update: dict[str, Any] = {"key": state.key, **state.as_dict()}
        for queue in tuple(self._subscriber_queues):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(copy.deepcopy(update))
        for callback in tuple(self._callbacks):
            try:
                returned = callback(copy.deepcopy(update))
                if inspect.isawaitable(returned):
                    future = asyncio.ensure_future(returned)
                    future.add_done_callback(self._callback_done)
            except Exception:
                LOGGER.exception("state update callback failed")

    @staticmethod
    def _callback_done(task: asyncio.Future[Any]) -> None:
        """Log an asynchronous callback failure without breaking polling."""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            LOGGER.exception("async state update callback failed")

    async def _write_state_file(self) -> None:
        """Atomically persist a complete snapshot when state output is enabled."""
        if self.config is None:
            return
        state_path = self.config_store.resolve_relative_path(self.config.get("state_file"))
        if state_path is None:
            return
        async with self._state_write_lock:
            await atomic_json_write(state_path, self.snapshot())
