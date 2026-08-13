"""Single-owner tier scheduling and confirmed snapshot publication."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from wolf_325 import CommunicationError, WolfCWL2

from .const import (
    CONF_FAST_INTERVAL,
    CONF_RECONCILE_INTERVAL,
    CONF_SLOW_INTERVAL,
    CONF_STATIC_INTERVAL,
    DEFAULT_OPTIONS,
)
from .repairs import clear_entry_issue, create_entry_issue
from .storage import EntryStore

LOGGER = logging.getLogger(__name__)
TIERS = ("fast", "slow", "static")


class IdentityMismatchError(UpdateFailed):
    """Report a live serial that no longer matches the config entry."""


@dataclass(frozen=True, slots=True)
class CoordinatorData:
    """Describe one immutable confirmed coordinator publication.

    Attributes:
        snapshot: Isolated public client snapshot after the update.
        refreshed_tiers: Tiers read during this coordinator cycle.
        tier_last_success: Monotonic success time by tier.
    """

    snapshot: dict[str, Any]
    refreshed_tiers: tuple[str, ...]
    tier_last_success: tuple[tuple[str, float], ...]
    reconcile_errors: tuple[str, ...] = ()
    desired_pending: int = 0


class WolfCWL2Coordinator(DataUpdateCoordinator[CoordinatorData]):
    """Batch due polling tiers behind one config-entry operation lock."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        controller: WolfCWL2,
        operation_lock: asyncio.Lock,
        options: Mapping[str, Any],
        expected_serial: str,
        *,
        store: EntryStore,
        authority: str,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize one coordinator and monotonic tier schedule.

        Args:
            hass: Home Assistant instance owning scheduling.
            entry: Config entry owning this coordinator.
            controller: Started public client with background loops disabled.
            operation_lock: Whole-operation serialization lock for this entry.
            options: Validated polling policy.
            expected_serial: Serial identity verified by the config flow.
            store: Loaded per-entry desired-state authorization owner.
            authority: Canonical runtime authority mode.
            time_fn: Injectable monotonic clock for deterministic tests.
        """
        policy = {**DEFAULT_OPTIONS, **dict(options)}
        self.controller = controller
        self.operation_lock = operation_lock
        self.expected_serial = expected_serial
        self.store = store
        self.authority = authority
        self._time = time_fn
        self._intervals = {
            "fast": float(policy[CONF_FAST_INTERVAL]),
            "slow": float(policy[CONF_SLOW_INTERVAL]),
            "static": float(policy[CONF_STATIC_INTERVAL]),
        }
        self._next_due = {tier: 0.0 for tier in TIERS}
        self._reconcile_interval = float(policy[CONF_RECONCILE_INTERVAL])
        self._next_reconcile = 0.0
        self._verified_generation = -1
        self._reconciled_generation = -1
        self._last_success: dict[str, float] = {}
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{entry.title} data",
            update_interval=timedelta(seconds=min(self._intervals.values())),
            always_update=False,
        )

    async def _async_update_data(self) -> CoordinatorData:
        """Poll all currently due tiers once and verify live identity.

        Returns:
            Immutable confirmed snapshot and tier freshness facts.

        Raises:
            UpdateFailed: If communication or serial verification fails.
        """
        now = self._time()
        due = tuple(tier for tier in TIERS if now >= self._next_due[tier])
        reconcile_due = (
            self.authority == "persistent"
            and self.store.desired_active
            and now >= self._next_reconcile
        )
        if not due and not reconcile_due and self.data is not None:
            return self.data
        reconcile_errors: tuple[str, ...] = ()
        try:
            async with self.operation_lock:
                await self.controller.poll_once(due)
                generation = int(
                    self.controller.snapshot()["connection_generation"]
                )
                if generation != self._verified_generation:
                    await self.controller.refresh("serial_number")
                    self._verified_generation = generation
                serial = self.controller.get_value("serial_number")
                if serial != self.expected_serial:
                    create_entry_issue(
                        self.hass,
                        "identity_mismatch",
                        self.config_entry.entry_id,
                    )
                    raise IdentityMismatchError(
                        "live appliance identity does not match config entry"
                    )
                clear_entry_issue(
                    self.hass,
                    "identity_mismatch",
                    self.config_entry.entry_id,
                )
                if reconcile_due:
                    for key in self.controller.desired:
                        await self.controller.refresh(key)
                    result = await self.controller.apply_desired(
                        force=generation != self._reconciled_generation,
                        raise_on_error=False,
                    )
                    reconcile_errors = tuple(sorted(result["errors"]))
                    if not reconcile_errors:
                        self._reconciled_generation = generation
        except CommunicationError as exc:
            raise UpdateFailed("configured appliance unavailable") from exc
        for tier in due:
            self._last_success[tier] = now
            self._next_due[tier] = now + self._intervals[tier]
        if reconcile_due:
            self._next_reconcile = now + self._reconcile_interval
        return CoordinatorData(
            snapshot=self.controller.snapshot(),
            refreshed_tiers=due,
            tier_last_success=tuple(sorted(self._last_success.items())),
            reconcile_errors=reconcile_errors,
            desired_pending=(
                len(self.controller.desired)
                if reconcile_errors or not self.store.desired_active
                else 0
            ),
        )

    def defer_reconciliation(self) -> None:
        """Advance reconciliation after an explicit successful desired apply.

        Returns:
            None after updating only coordinator-owned monotonic deadlines.
        """
        self._next_reconcile = self._time() + self._reconcile_interval
        generation = int(self.controller.snapshot()["connection_generation"])
        self._reconciled_generation = generation

    def invalidate_after_appliance_reset(self) -> None:
        """Invalidate cached availability and make every tier immediately due.

        Returns:
            None after scheduling the normal coordinator path to reconnect.
        """
        self._next_due = {tier: 0.0 for tier in TIERS}
        self._verified_generation = -1
        self.async_set_update_error(UpdateFailed("appliance reset command dispatched"))

    def tier_is_fresh(self, tier: str) -> bool:
        """Return whether a tier succeeded within two configured intervals.

        Args:
            tier: Canonical fast, slow, or static tier.

        Returns:
            ``True`` when the tier has a recent successful refresh.
        """
        last_success = self._last_success.get(tier)
        return last_success is not None and (
            self._time() - last_success <= self._intervals[tier] * 2
        )
