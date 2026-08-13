"""Opt-in read-only audit against the physical WOLF CWL-2-325 appliance."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from wolf_325 import (
    REGISTERS,
    CommunicationError,
    RemoteModbusError,
    WolfCWL2,
)


def _device_config() -> Path:
    """Return the explicitly opted-in hardware configuration or skip the test."""
    configured = os.environ.get("WOLF_325_DEVICE_CONFIG")
    if not configured:
        pytest.skip("set WOLF_325_DEVICE_CONFIG to run the physical-device audit")
    return Path(configured).expanduser().resolve()


def _report_path() -> Path:
    """Return the requested audit output path or a stable temporary default."""
    configured = os.environ.get(
        "WOLF_325_DEVICE_REPORT", "/tmp/wolf-325-device-audit.json"
    )
    return Path(configured).expanduser().resolve()


@pytest.mark.hardware
async def test_every_catalogue_value_against_physical_device() -> None:
    """Read and classify all 154 definitions without issuing any Modbus write."""
    controller = WolfCWL2(_device_config())
    await controller.load_config()
    controller._read_only = True
    values: dict[str, dict[str, Any]] = {}
    connection_failure: str | None = None
    try:
        for key, register in sorted(
            REGISTERS.items(),
            key=lambda item: (item[1].table, item[1].address, item[0]),
        ):
            for attempt in range(3):
                try:
                    await controller.refresh(key)
                    state = controller.get_state(key)
                    if state["available"]:
                        outcome = "available"
                    elif register.optional and str(state["error"]).startswith(
                        "short response"
                    ):
                        outcome = "unsupported_optional"
                    else:
                        outcome = "decode_error"
                    values[key] = {
                        "address": register.address,
                        "table": register.table,
                        "optional": register.optional,
                        "poll": register.poll,
                        "outcome": outcome,
                        **state,
                    }
                    break
                except RemoteModbusError as exc:
                    values[key] = {
                        "address": register.address,
                        "table": register.table,
                        "optional": register.optional,
                        "poll": register.poll,
                        "outcome": (
                            "unsupported_optional" if register.optional else "failed"
                        ),
                        "value": None,
                        "raw": None,
                        "unit": register.unit,
                        "available": False,
                        "updated_at": None,
                        "error": str(exc),
                    }
                    break
                except CommunicationError as exc:
                    if attempt < 2:
                        continue
                    values[key] = {
                        "address": register.address,
                        "table": register.table,
                        "optional": register.optional,
                        "poll": register.poll,
                        "outcome": "failed",
                        "value": None,
                        "raw": None,
                        "unit": register.unit,
                        "available": False,
                        "updated_at": None,
                        "error": str(exc),
                    }
                    if not controller.connected:
                        connection_failure = f"{key}: {exc}"
            if connection_failure is not None:
                break
    finally:
        await controller.stop()

    counts = {
        outcome: sum(item["outcome"] == outcome for item in values.values())
        for outcome in (
            "available",
            "unsupported_optional",
            "decode_error",
            "failed",
        )
    }
    failed_keys = [
        key for key, item in values.items() if item["outcome"] == "failed"
    ]
    required_failures = [
        key
        for key, item in values.items()
        if item["outcome"] != "available" and not item["optional"]
    ]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "config": str(_device_config()),
        "read_only": True,
        "catalogue_count": len(REGISTERS),
        "attempted_count": len(values),
        "counts": counts,
        "connection_failure": connection_failure,
        "failed_keys": failed_keys,
        "required_failures": required_failures,
        "values": values,
    }
    report_path = _report_path()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    assert connection_failure is None
    assert len(values) == len(REGISTERS) == 154
    assert not failed_keys
    assert not required_failures


@pytest.mark.hardware
async def test_normal_block_polling_against_physical_device() -> None:
    """Poll all normal tiers while isolating optional partial block responses."""
    controller = WolfCWL2(_device_config())
    await controller.load_config()
    controller._read_only = True
    try:
        await controller.poll_once()
        required_unavailable = [
            key
            for key, register in REGISTERS.items()
            if register.poll != "never"
            and not register.optional
            and not controller.get_state(key)["available"]
        ]
        assert required_unavailable == []
        assert controller.get_state("extension_software_version")["available"] is True
        extension_hardware = controller.get_state("extension_hardware_version")
        assert extension_hardware["available"] is False
        assert "short response" in str(extension_hardware["error"])
    finally:
        await controller.stop()
