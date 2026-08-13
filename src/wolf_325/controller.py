"""Public asynchronous WOLF CWL-2-325 controller and state cache."""

from __future__ import annotations

import asyncio
import copy
import logging
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from .catalogue import REGISTERS, resolve_register_name
from .config import ConfigStore
from .errors import CommunicationError
from .polling import PollingMixin
from .profile_engine import ProfileRepository
from .profiles import (
    MemoryProfileRepository,
    ProfileChanges,
    ProfileLoader,
    SavedProfile,
)
from .runtime_config import ConfigRepository, ConfigSaveCallback, RuntimeConfigStore
from .settings import SettingsMixin
from .state import UpdateCallback, ValueState
from .transport import TransportMixin
from .types import JSONScalar, JSONValue, PollTier
from .writes import WriteMixin

LOGGER = logging.getLogger("wolf_325")
class WolfCWL2(
    SettingsMixin,
    WriteMixin,
    PollingMixin,
    TransportMixin,
):
    """Control a WOLF CWL-2-325 asynchronously and cache all documented values."""

    def __init__(
        self,
        config_path: str | Path = "wolf_cwl2_config.json",
        *,
        config_store: ConfigRepository | None = None,
        profile_repository: ProfileRepository | None = None,
    ) -> None:
        """Initialize an unloaded controller over file or injected repositories.

        Args:
            config_path: Legacy JSON configuration path used when no repository
                is injected.
            config_store: Optional host-owned configuration repository.
            profile_repository: Optional host-owned profile repository.
        """
        self.config_store: ConfigRepository = config_store or ConfigStore(config_path)
        self.config: dict[str, Any] | None = None
        self.profile_loader: ProfileRepository | None = profile_repository
        self._client: AsyncModbusTcpClient | Any | None = None
        self._io_lock = asyncio.Lock()
        self._state_write_lock = asyncio.Lock()
        self._values = {
            key: ValueState(key=key, unit=register.unit)
            for key, register in REGISTERS.items()
        }
        self._running = False
        self._read_only = False
        self._tasks: list[asyncio.Task[Any]] = []
        self._stop_event = asyncio.Event()
        self._callbacks: set[UpdateCallback] = set()
        self._subscriber_queues: set[asyncio.Queue[dict[str, Any]]] = set()
        self._connection_generation = 0
        self._last_restored_generation = -1
        self._last_connection_error: str | None = None
        self._last_poll_at: dict[str, str | None] = {
            "fast": None,
            "slow": None,
            "static": None,
        }

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        *,
        save_callback: ConfigSaveCallback | None = None,
        profile_repository: ProfileRepository | None = None,
    ) -> "WolfCWL2":
        """Construct a controller without a client-owned configuration file.

        Args:
            config: Partial or complete normalized controller configuration.
            save_callback: Awaited host persistence callback for configuration
                and desired lineage.
            profile_repository: Host-owned profile catalogue, or an empty
                in-memory repository when omitted.

        Returns:
            Unloaded controller ready for explicit lifecycle ownership.
        """
        return cls(
            config_store=RuntimeConfigStore(config, save_callback=save_callback),
            profile_repository=profile_repository or MemoryProfileRepository(),
        )
    async def load_config(self) -> dict[str, Any]:
        """Load configuration and initialize its relative profile directory."""
        self.config = await self.config_store.load()
        if self.profile_loader is None:
            profiles_path = self.config_store.resolve_relative_path(
                self.config.get("profiles_dir")
            )
            assert profiles_path is not None
            self.profile_loader = ProfileLoader(profiles_path)
        return copy.deepcopy(self.config)

    async def start(
        self,
        *,
        restore: bool | None = None,
        background: bool = True,
        read_only: bool = False,
        initial_poll: bool = True,
    ) -> None:
        """Start lifecycle with explicit polling, restore, and task ownership."""
        if self._running:
            return
        if self.config is None:
            await self.load_config()
        self._read_only = read_only
        self._stop_event.clear()
        self._running = True
        if initial_poll:
            try:
                await self.poll_once()
            except CommunicationError as exc:
                LOGGER.warning("initial Modbus poll failed: %s", exc)
        should_restore = bool(self.config["persistence"]["restore_on_startup"])
        if restore is not None:
            should_restore = restore
        if should_restore and not self._read_only:
            result = await self.apply_desired(force=True, raise_on_error=False)
            if not result["errors"]:
                self._last_restored_generation = self._connection_generation
        await self._write_state_file()
        if background:
            polling = self.config["polling"]
            self._tasks = [
                asyncio.create_task(
                    self._poll_loop(tier, float(polling[f"{tier}_interval_seconds"])),
                    name=f"wolf-cwl2-{tier}-poll",
                )
                for tier in ("fast", "slow", "static")
            ]
            if not self._read_only:
                self._tasks.append(
                    asyncio.create_task(
                        self._reconcile_loop(), name="wolf-cwl2-reconcile"
                    )
                )

    async def stop(self) -> None:
        """Stop background work, close the transport, and persist final state."""
        if not self._running and self._client is None:
            return
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        async with self._io_lock:
            self._close_client_locked()
        self._running = False
        await self._write_state_file()

    async def __aenter__(self) -> "WolfCWL2":
        """Start the controller when entering an async context."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        """Stop the controller when leaving an async context."""
        await self.stop()

    @property
    def connected(self) -> bool:
        """Return whether the current Modbus client reports a live connection."""
        return bool(self._client is not None and self._client.connected)

    @property
    def desired(self) -> dict[str, JSONScalar]:
        """Return an isolated copy of currently owned desired settings."""
        if self.config is None:
            return {}
        return copy.deepcopy(self.config.get("desired", {}))

    def get_value(self, name: str, default: Any = None) -> Any:
        """Return a cached value or the supplied default when unavailable."""
        state = self._values[resolve_register_name(name)]
        return state.value if state.available else default

    def get_state(self, name: str) -> dict[str, Any]:
        """Return an isolated public state record for one named value."""
        return copy.deepcopy(self._values[resolve_register_name(name)].as_dict())

    def snapshot(self, *, available_only: bool = False) -> dict[str, Any]:
        """Return a timestamped JSON-compatible snapshot of controller state."""
        values = {
            key: state.as_dict()
            for key, state in sorted(self._values.items())
            if not available_only or state.available
        }
        return {
            "connected": self.connected,
            "connection_generation": self._connection_generation,
            "last_connection_error": self._last_connection_error,
            "last_poll_at": copy.deepcopy(self._last_poll_at),
            "last_profile": self.config.get("last_profile") if self.config else None,
            "desired": self.desired,
            "values": values,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def subscribe(self, callback: UpdateCallback) -> Callable[[], None]:
        """Register a state callback and return its unsubscribe function."""
        self._callbacks.add(callback)

        def unsubscribe() -> None:
            """Remove the callback from future update delivery."""
            self._callbacks.discard(callback)

        return unsubscribe

    async def updates(
        self, *, queue_size: int = 200
    ) -> AsyncIterator[dict[str, JSONValue]]:
        """Yield changed value records through a bounded per-subscriber queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=queue_size)
        self._subscriber_queues.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscriber_queues.discard(queue)

    async def poll_once(
        self, tiers: Sequence[PollTier] = ("fast", "slow", "static")
    ) -> None:
        """Poll the requested tiers once, ignoring the non-polled never tier."""
        for tier in tiers:
            if tier != "never":
                await self._poll_tier(tier)

    async def refresh(self, name: str) -> JSONValue | None:
        """Read one named value immediately and return its decoded value."""
        key = resolve_register_name(name)
        await self._read_definition(REGISTERS[key])
        return self._values[key].value

    async def preview_profile_changes(self) -> ProfileChanges:
        """Return the desired-state delta from the last loaded profile."""
        if self.config is None:
            await self.load_config()
        assert self.config is not None
        assert self.profile_loader is not None
        return await self.profile_loader.capture_changes(
            self.desired,
            last_profile=self.config.get("last_profile"),
        )

    async def save_profile(
        self,
        name: str,
        *,
        description: str = "",
        overwrite: bool = False,
    ) -> SavedProfile:
        """Save current desired changes as a derived or standalone profile.

        Args:
            name: New profile name without a JSON extension.
            description: Human-readable description stored in the profile.
            overwrite: Whether to replace an existing profile of the same name.

        Returns:
            Metadata and delta for the atomically saved profile.
        """
        if self.config is None:
            await self.load_config()
        assert self.config is not None
        assert self.profile_loader is not None
        return await self.profile_loader.save_changes(
            name,
            self.desired,
            last_profile=self.config.get("last_profile"),
            description=description,
            overwrite=overwrite,
        )
