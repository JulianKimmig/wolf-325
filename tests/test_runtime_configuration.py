"""Behavior tests for host-neutral controller configuration and repositories."""

from __future__ import annotations

import asyncio
import copy
import importlib.metadata
import threading
from pathlib import Path

from wolf_325 import (
    DEFAULT_CONFIG,
    MemoryProfileRepository,
    RuntimeConfigStore,
    WolfCWL2,
    atomic_json_write,
    example_profile_documents,
)

from conftest import FakeClient


def test_textual_is_only_a_declared_tui_extra() -> None:
    """Base metadata pins transport and keeps the HA-irrelevant TUI optional."""
    requirements = importlib.metadata.requires("wolf-325") or []
    textual = [item for item in requirements if item.lower().startswith("textual")]
    pymodbus = [
        item for item in requirements if item.lower().startswith("pymodbus")
    ]

    assert textual
    assert all("extra == 'tui'" in item for item in textual)
    assert pymodbus == ["pymodbus==3.14.0"]


async def test_runtime_store_merges_and_canonicalizes_without_a_file() -> None:
    """Runtime configuration preserves normal validation without filesystem I/O."""
    supplied = {
        "schema_version": 1,
        "connection": {"host": "runtime-gateway"},
        "state_file": None,
        "profiles_dir": None,
        "desired": {"fan_level": "HIGH"},
    }

    store = RuntimeConfigStore(supplied)
    loaded = await store.load()

    assert loaded["connection"]["port"] == 502
    assert loaded["desired"] == {"remote_ventilation_level": "high"}
    assert store.resolve_relative_path("anything.json") is None


async def test_runtime_store_awaits_persistence_before_returning() -> None:
    """A host callback durably observes desired state before update completes."""
    saved: list[dict[str, object]] = []

    async def save(payload: dict[str, object]) -> None:
        """Record a host-owned durable payload."""
        await asyncio.sleep(0)
        saved.append(copy.deepcopy(payload))

    store = RuntimeConfigStore(DEFAULT_CONFIG, save_callback=save)
    await store.load()

    desired = await store.update_desired(
        {"remote_airflow_m3h": 170}, last_profile="day"
    )

    assert desired == {"remote_airflow_m3h": 170}
    assert saved[-1]["desired"] == desired
    assert saved[-1]["last_profile"] == "day"


async def test_memory_profiles_share_file_profile_semantics() -> None:
    """In-memory profiles inherit and capture through the common profile engine."""
    repository = MemoryProfileRepository(
        {
            "base": {
                "replace": True,
                "settings": {
                    "remote_control_mode": "level",
                    "remote_ventilation_level": "normal",
                },
            }
        }
    )

    resolved = await repository.load("base")
    saved = await repository.save_changes(
        "derived",
        {
            "remote_control_mode": "level",
            "remote_ventilation_level": "high",
        },
        last_profile="base",
        description="Higher flow",
    )

    assert resolved.replace is True
    assert saved.path is None
    assert saved.changes.extends == "base"
    assert saved.changes.settings == {"remote_ventilation_level": "high"}
    assert (await repository.load("derived")).settings == {
        "remote_control_mode": "level",
        "remote_ventilation_level": "high",
    }


async def test_example_profiles_are_reusable_outside_the_cli() -> None:
    """A host can seed and resolve the canonical example profile catalogue."""
    repository = MemoryProfileRepository(example_profile_documents())

    summer = await repository.load("summer-night")

    assert summer.sources == ["night", "summer-night"]
    assert summer.settings["remote_ventilation_level"] == "low"
    assert summer.settings["bypass_mode"] == "open"


async def test_direct_controller_start_can_skip_the_initial_poll() -> None:
    """A host-owned coordinator can be the sole first-poll owner."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["connection"]["host"] = "runtime-gateway"
    config["state_file"] = None
    controller = WolfCWL2.from_config(config)
    client = FakeClient()
    controller._client = client

    await controller.start(
        initial_poll=False,
        restore=False,
        background=False,
        read_only=True,
    )

    assert client.reads == []
    assert controller.snapshot()["connected"] is True
    await controller.stop()


async def test_atomic_json_write_runs_the_durable_writer_off_loop(
    tmp_path: Path, monkeypatch,
) -> None:
    """Durable filesystem work executes outside the event-loop thread."""
    import wolf_325.config as config_module

    event_loop_thread = threading.get_ident()
    writer_threads: list[int] = []

    def record_writer(path: Path, payload: dict[str, object]) -> None:
        """Record the worker identity instead of touching the filesystem."""
        writer_threads.append(threading.get_ident())

    monkeypatch.setattr(config_module, "atomic_json_write_sync", record_writer)

    await atomic_json_write(tmp_path / "state.json", {"value": 1})

    assert writer_threads
    assert writer_threads[0] != event_loop_thread
