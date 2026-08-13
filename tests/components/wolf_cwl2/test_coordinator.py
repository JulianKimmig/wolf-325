"""Tests for monotonic tier scheduling, freshness, outage, and recovery."""

from __future__ import annotations

import asyncio
import copy

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN
from custom_components.wolf_cwl2.coordinator import WolfCWL2Coordinator
from custom_components.wolf_cwl2.storage import EntryStore
from wolf_325 import DEFAULT_CONFIG, WolfCWL2

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS


class FakeClock:
    """Expose a mutable monotonic time source for coordinator tests."""

    def __init__(self) -> None:
        """Initialize monotonic time at zero seconds."""
        self.now = 0.0

    def __call__(self) -> float:
        """Return current simulated monotonic seconds.

        Returns:
            Mutable simulated monotonic time.
        """
        return self.now


async def test_coordinator_batches_due_tiers_skips_bursts_and_recovers(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Poll due tiers once, expose freshness, and recover after transport loss.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["connection"].update(CONNECTION)
    config["connection"]["request_retries"] = 0
    config["connection"]["client_retries"] = 0
    config["state_file"] = None
    config["profiles_dir"] = None
    controller = WolfCWL2.from_config(config)
    await controller.start(
        restore=False,
        background=False,
        read_only=True,
        initial_poll=False,
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Coordinator test",
        unique_id="123456789012",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )
    clock = FakeClock()
    store = EntryStore(hass, entry.entry_id)
    await store.async_load()
    await store.async_transition_authority("monitor_only")
    coordinator = WolfCWL2Coordinator(
        hass,
        entry,
        controller,
        asyncio.Lock(),
        DEFAULT_OPTIONS,
        "123456789012",
        store=store,
        authority="monitor_only",
        time_fn=clock,
    )
    try:
        await coordinator.async_refresh()
        assert coordinator.last_update_success
        assert coordinator.data.refreshed_tiers == ("fast", "slow", "static")
        initial_reads = len(fake_gateway.reads) + len(fake_gateway.holding_reads)

        clock.now = 4.9
        await coordinator.async_refresh()
        assert len(fake_gateway.reads) + len(fake_gateway.holding_reads) == initial_reads

        clock.now = 5
        await coordinator.async_refresh()
        assert coordinator.data.refreshed_tiers == ("fast",)
        assert coordinator.tier_is_fresh("fast")

        clock.now = 60
        before_skipped_burst = len(fake_gateway.reads) + len(fake_gateway.holding_reads)
        await coordinator.async_refresh()
        assert coordinator.data.refreshed_tiers == ("fast", "slow")
        assert len(fake_gateway.reads) + len(fake_gateway.holding_reads) > before_skipped_burst

        fake_gateway.fails_reads = True
        clock.now = 65
        await coordinator.async_refresh()
        assert not coordinator.last_update_success
        assert not controller.connected

        fake_gateway.fails_reads = False
        clock.now = 70
        await coordinator.async_refresh()
        assert coordinator.last_update_success
        assert controller.connected

        clock.now = 181
        assert not coordinator.tier_is_fresh("slow")
        assert coordinator.tier_is_fresh("static")
    finally:
        await coordinator.async_shutdown()
        await controller.stop()
