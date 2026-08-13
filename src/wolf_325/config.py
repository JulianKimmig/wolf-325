"""Atomic JSON configuration persistence and schema validation."""

from __future__ import annotations

import asyncio
import contextlib
import copy
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from .async_utils import run_in_worker
from .catalogue import resolve_register_name
from .errors import ConfigError
from .types import JSONScalar
from .validation import normalize_settings, validate_cross_settings

DEFAULT_CONFIG: Final[dict[str, Any]] = {
    "schema_version": 1,
    "connection": {
        "host": "192.168.1.200",
        "port": 502,
        "device_id": 20,
        "address_offset": 0,
        "transport": "modbus_tcp",
        "timeout_seconds": 3.0,
        "client_retries": 2,
        "request_retries": 2,
        "reconnect_delay_seconds": 1.0,
        "reconnect_delay_max_seconds": 30.0,
    },
    "polling": {
        "fast_interval_seconds": 5.0,
        "slow_interval_seconds": 60.0,
        "static_interval_seconds": 300.0,
        "reconcile_interval_seconds": 30.0,
        "read_holding_registers": True,
        "read_extension_registers": True,
    },
    "persistence": {
        "restore_on_startup": True,
        "restore_on_reconnect": True,
        "enforce_desired_state": True,
        "verify_writes": True,
        "verify_attempts": 5,
        "verify_delay_seconds": 0.25,
    },
    "profiles_dir": "profiles",
    "state_file": "wolf_state.json",
    "desired": {},
    "last_profile": None,
}


def deep_merge(defaults: Mapping[str, Any], supplied: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge supplied values over an independent defaults copy."""
    result = copy.deepcopy(dict(defaults))
    for key, value in supplied.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def atomic_json_write_sync(path: Path, payload: Mapping[str, Any]) -> None:
    """Durably replace a JSON file with a fully flushed temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        with contextlib.suppress(OSError):
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


async def atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    """Write JSON atomically without blocking the caller's event loop."""
    await run_in_worker(atomic_json_write_sync, path, copy.deepcopy(dict(payload)))


async def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object asynchronously and translate file errors to ConfigError."""

    def read() -> dict[str, Any]:
        """Perform the blocking JSON read in a worker thread."""
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except FileNotFoundError as exc:
            raise ConfigError(f"configuration file does not exist: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ConfigError(f"top-level JSON value in {path} must be an object")
        return loaded

    return await run_in_worker(read)


def validate_config(config: Mapping[str, Any]) -> None:
    """Validate schema and operational bounds for a merged configuration."""
    ConfigStore._validate(config)


class ConfigStore:
    """Concurrency-safe, atomically persisted JSON configuration store."""

    def __init__(self, path: str | Path) -> None:
        """Initialize a store for a resolved configuration path."""
        self.path = Path(path).expanduser().resolve()
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    @property
    def data(self) -> dict[str, Any]:
        """Return an isolated copy of loaded data or fail before load."""
        if self._data is None:
            raise ConfigError("configuration has not been loaded")
        return copy.deepcopy(self._data)

    async def load(self) -> dict[str, Any]:
        """Read, merge, validate, and canonicalize the configuration."""
        async with self._lock:
            supplied = await read_json(self.path)
            merged = deep_merge(DEFAULT_CONFIG, supplied)
            self._validate(merged)
            merged["desired"] = normalize_settings(
                merged.get("desired", {}), require_restorable=True
            )
            self._data = merged
            return copy.deepcopy(merged)

    async def save(self) -> None:
        """Persist the current loaded configuration atomically."""
        async with self._lock:
            if self._data is None:
                raise ConfigError("configuration has not been loaded")
            await atomic_json_write(self.path, self._data)

    async def update_desired(
        self,
        patch: Mapping[str, JSONScalar] | None = None,
        *,
        unset: Sequence[str] = (),
        replace: bool = False,
        last_profile: str | None = None,
    ) -> dict[str, JSONScalar]:
        """Atomically merge, release, or replace owned desired settings."""
        async with self._lock:
            if self._data is None:
                raise ConfigError("configuration has not been loaded")
            current: dict[str, JSONScalar] = (
                {} if replace else dict(self._data.get("desired", {}))
            )
            for name in unset:
                current.pop(resolve_register_name(name), None)
            if patch:
                current.update(patch)
            validate_cross_settings(current)
            self._data["desired"] = current
            self._data["last_profile"] = last_profile
            await atomic_json_write(self.path, self._data)
            return copy.deepcopy(current)

    def resolve_relative_path(self, configured: str | None) -> Path | None:
        """Resolve a configured file relative to the configuration directory."""
        if configured is None or not str(configured).strip():
            return None
        path = Path(str(configured)).expanduser()
        if not path.is_absolute():
            path = self.path.parent / path
        return path.resolve()

    @staticmethod
    def _validate(config: Mapping[str, Any]) -> None:
        """Validate schema and operational bounds for a merged configuration."""
        if config.get("schema_version") != 1:
            raise ConfigError("only schema_version 1 is supported")
        connection = config.get("connection")
        polling = config.get("polling")
        persistence = config.get("persistence")
        if not all(isinstance(value, Mapping) for value in (connection, polling, persistence)):
            raise ConfigError("connection, polling, and persistence must be JSON objects")
        assert isinstance(connection, Mapping)
        assert isinstance(polling, Mapping)
        assert isinstance(persistence, Mapping)
        if not str(connection.get("host", "")).strip():
            raise ConfigError("connection.host must not be empty")
        if not 1 <= int(connection.get("port", 0)) <= 65535:
            raise ConfigError("connection.port must be 1..65535")
        if not 1 <= int(connection.get("device_id", 0)) <= 247:
            raise ConfigError("connection.device_id must be 1..247")
        if int(connection.get("address_offset", 0)) not in (-1, 0):
            raise ConfigError("connection.address_offset must be 0 (normal) or -1")
        if connection.get("transport") not in {"modbus_tcp", "rtu_over_tcp"}:
            raise ConfigError("connection.transport must be 'modbus_tcp' or 'rtu_over_tcp'")
        for key in (
            "fast_interval_seconds", "slow_interval_seconds",
            "static_interval_seconds", "reconcile_interval_seconds",
        ):
            if float(polling.get(key, 0)) <= 0:
                raise ConfigError(f"polling.{key} must be greater than zero")
        if int(persistence.get("verify_attempts", 0)) < 1:
            raise ConfigError("persistence.verify_attempts must be at least 1")
        if not isinstance(config.get("desired", {}), Mapping):
            raise ConfigError("desired must be a JSON object")
