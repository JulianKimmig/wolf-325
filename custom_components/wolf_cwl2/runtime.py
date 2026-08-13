"""Typed ownership bundle for one loaded Home Assistant config entry."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry

from wolf_325 import WolfCWL2

from .coordinator import WolfCWL2Coordinator
from .storage import EntryStore


@dataclass(slots=True)
class EntryRuntime:
    """Own all mutable resources scoped to one loaded config entry.

    Attributes:
        controller: Public host-neutral appliance client.
        coordinator: Sole Home Assistant polling scheduler.
        store: Per-entry durable desired/profile transaction owner.
        operation_lock: Whole-operation serialization lock.
        authority: Configured monitor, temporary, or persistent mode.
        profile_names: Sorted HA-owned profile catalogue names.
        last_applied_profile: Last successful HA application in this runtime.
        scheduler_unsubscribe: Retained listener removal callback.
        stopping: Whether unload has begun.
    """

    controller: WolfCWL2
    coordinator: WolfCWL2Coordinator
    store: EntryStore
    operation_lock: asyncio.Lock
    authority: str
    profile_names: tuple[str, ...]
    last_applied_profile: str | None
    scheduler_unsubscribe: Callable[[], None]
    stopping: bool = False


WolfCWL2ConfigEntry: TypeAlias = ConfigEntry[EntryRuntime]
