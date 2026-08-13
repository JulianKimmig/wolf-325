"""Behavior tests for versioned per-entry Home Assistant storage."""

from __future__ import annotations

import copy

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.wolf_cwl2.storage import EntryStore, EntryStoreError
from custom_components.wolf_cwl2.storage_models import (
    STORE_SCHEMA_VERSION,
    new_store_payload,
)
from wolf_325 import DEFAULT_CONFIG


async def test_home_assistant_store_preserves_payload_shape(
    hass: HomeAssistant,
) -> None:
    """Qualify Home Assistant's external Store serialization for our payload.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    payload = new_store_payload()
    raw: Store[dict[str, object]] = Store(
        hass,
        version=STORE_SCHEMA_VERSION,
        key="wolf_cwl2.shape-qualification",
        private=True,
        atomic_writes=True,
    )
    await raw.async_save(payload)
    assert await raw.async_load() == payload


async def test_entry_store_seeds_and_round_trips_desired_and_profiles(
    hass: HomeAssistant,
) -> None:
    """Persist desired lineage and portable profiles across owner recreation.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    owner = EntryStore(hass, "entry-a")
    await owner.async_load()
    assert owner.revision == 1
    assert await owner.profile_repository.list_profiles() == [
        "away",
        "boost",
        "night",
        "normal",
        "summer-night",
    ]

    config = copy.deepcopy(DEFAULT_CONFIG)
    config["desired"] = {"bypass_mode": "open"}
    config["last_profile"] = "normal"
    await owner.async_save_config(config)
    await owner.profile_repository.save_changes(
        "summer",
        config["desired"],
        last_profile=None,
        description="Summer bypass",
    )
    await owner.async_set_last_applied_profile("summer")
    await owner.profile_repository.save_changes(
        "away",
        {"bypass_mode": "closed"},
        last_profile=None,
        description="Customized away profile",
        overwrite=True,
    )

    reloaded = EntryStore(hass, "entry-a")
    await reloaded.async_load()
    assert reloaded.revision == 5
    assert reloaded.desired == {"bypass_mode": "open"}
    assert reloaded.last_profile == "normal"
    assert reloaded.last_applied_profile == "summer"
    assert (await reloaded.profile_repository.load("summer")).settings == {
        "bypass_mode": "open"
    }
    assert (await reloaded.profile_repository.load("away")).settings == {
        "bypass_mode": "closed"
    }


async def test_entry_stores_are_isolated_and_remove_only_the_target(
    hass: HomeAssistant,
) -> None:
    """Keep documents and deletion scoped to one config-entry identifier.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    first = EntryStore(hass, "entry-first")
    second = EntryStore(hass, "entry-second")
    await first.async_load()
    await second.async_load()
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["desired"] = {"bypass_mode": "closed"}
    await first.async_save_config(config)

    await first.async_remove()
    first_again = EntryStore(hass, "entry-first")
    second_again = EntryStore(hass, "entry-second")
    await first_again.async_load()
    await second_again.async_load()
    assert first_again.desired == {}
    assert second_again.revision == 1
    assert first_again.storage_key != second_again.storage_key


async def test_entry_store_rejects_missing_profile_markers(
    hass: HomeAssistant,
) -> None:
    """Prevent desired lineage or selector truth from naming absent profiles.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    owner = EntryStore(hass, "entry-markers")
    await owner.async_load()
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["last_profile"] = "missing"

    with pytest.raises(EntryStoreError, match="profile 'missing' does not exist"):
        await owner.async_save_config(config)
    with pytest.raises(EntryStoreError, match="profile 'missing' does not exist"):
        await owner.async_set_last_applied_profile("missing")
    assert owner.revision == 1


async def test_entry_store_rejects_unknown_forward_payload(
    hass: HomeAssistant,
) -> None:
    """Fail closed when stored integration data has a future schema.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    raw: Store[dict[str, object]] = Store(
        hass,
        version=STORE_SCHEMA_VERSION,
        key="wolf_cwl2.entry-forward",
        private=True,
        atomic_writes=True,
    )
    await raw.async_save({"schema_version": 99, "revision": 7})

    owner = EntryStore(hass, "entry-forward")
    with pytest.raises(EntryStoreError, match="unsupported store schema"):
        await owner.async_load()


async def test_entry_store_migrates_actual_version_one_payload_without_loss(
    hass: HomeAssistant,
) -> None:
    """Upgrade legacy desired/profile data while leaving ownership dormant.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    payload = new_store_payload()
    payload["schema_version"] = 1
    payload["revision"] = 7
    payload["desired"] = {"bypass_mode": "open"}
    payload["last_profile"] = "normal"
    payload["last_applied_profile"] = "normal"
    payload.pop("desired_active")
    payload.pop("last_authority")
    raw: Store[dict[str, object]] = Store(
        hass,
        version=1,
        key="wolf_cwl2.entry-legacy",
        private=True,
        atomic_writes=True,
    )
    await raw.async_save(payload)

    owner = EntryStore(hass, "entry-legacy")
    await owner.async_load()
    assert owner.revision == 8
    assert owner.desired == {"bypass_mode": "open"}
    assert owner.last_profile == "normal"
    assert owner.last_applied_profile == "normal"
    assert not owner.desired_active

    current: Store[dict[str, object]] = Store(
        hass,
        version=STORE_SCHEMA_VERSION,
        key="wolf_cwl2.entry-legacy",
        private=True,
        atomic_writes=True,
    )
    persisted = await current.async_load()
    assert persisted is not None
    assert persisted["schema_version"] == STORE_SCHEMA_VERSION
    assert persisted["last_authority"] is None


async def test_entry_store_rejects_corrupt_profile_graph(
    hass: HomeAssistant,
) -> None:
    """Fail closed when stored profiles contain an inheritance cycle.

    Args:
        hass: Home Assistant test instance.

    Returns:
        None.
    """
    payload = new_store_payload()
    payload["profiles"] = {
        "first": {"extends": "second", "settings": {}},
        "second": {"extends": "first", "settings": {}},
    }
    raw: Store[dict[str, object]] = Store(
        hass,
        version=STORE_SCHEMA_VERSION,
        key="wolf_cwl2.entry-cycle",
        private=True,
        atomic_writes=True,
    )
    await raw.async_save(payload)

    owner = EntryStore(hass, "entry-cycle")
    with pytest.raises(EntryStoreError, match="stored integration data is invalid"):
        await owner.async_load()


async def test_failed_durable_verification_preserves_visible_state(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose no desired mutation when the external Store fails to replace data.

    Args:
        hass: Home Assistant test instance.
        monkeypatch: Pytest external-boundary patch helper.

    Returns:
        None.
    """
    owner = EntryStore(hass, "entry-failure")
    await owner.async_load()
    original_revision = owner.revision

    async def discard_write(_: object) -> None:
        """Simulate an external Store that returns without replacing data.

        Args:
            _: Serialized Store wrapper intentionally discarded.

        Returns:
            None.
        """

    monkeypatch.setattr(owner._store, "_async_write_data", discard_write)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["desired"] = {"bypass_mode": "automatic"}

    with pytest.raises(EntryStoreError, match="durable verification failed"):
        await owner.async_save_config(config)
    assert owner.desired == {}
    assert owner.revision == original_revision
