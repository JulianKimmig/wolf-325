"""Privacy-by-construction diagnostics and log sentinel tests."""

from __future__ import annotations

import copy
import json
import logging

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN
from custom_components.wolf_cwl2.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from wolf_325 import CommunicationError, DEFAULT_CONFIG

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_diagnostics_and_logs_exclude_every_sensitive_sentinel(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Expose useful categories without leaking any protected source value.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.
        caplog: Captured operational logging output.

    Returns:
        None.
    """
    sentinels = {
        "host": "sensitive-host.invalid",
        "port": "16543",
        "serial": "987654321098",
        "entry_id": "sensitive-entry-identifier",
        "profile": "sensitive-profile-name",
        "description": "sensitive profile description",
        "desired": "271",
        "live": "319",
        "raw": "65413",
        "exception": "sensitive gateway exception text",
    }
    fake_gateway.serial = sentinels["serial"]
    fake_gateway.input_words[4032] = int(sentinels["live"])
    fake_gateway.input_words[4036] = int(sentinels["raw"])
    fake_gateway.apply_identity()
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=sentinels["entry_id"],
        title="Private ventilation entry",
        unique_id=sentinels["serial"],
        data={
            **CONNECTION,
            "host": sentinels["host"],
            "port": int(sentinels["port"]),
        },
        options={**DEFAULT_OPTIONS, "authority": "persistent"},
    )
    entry.add_to_hass(hass)
    caplog.set_level(logging.INFO)
    assert await hass.config_entries.async_setup(entry.entry_id)

    config = copy.deepcopy(DEFAULT_CONFIG)
    config["desired"] = {"remote_airflow_m3h": int(sentinels["desired"])}
    await entry.runtime_data.store.async_save_config(config)
    await entry.runtime_data.store.profile_repository.save_changes(
        sentinels["profile"],
        config["desired"],
        last_profile=None,
        description=sentinels["description"],
    )
    fake_gateway.fails_reads = True
    fake_gateway.read_failure_message = sentinels["exception"]
    with pytest.raises(CommunicationError):
        await entry.runtime_data.controller.refresh("serial_number")

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    device_diagnostics = await async_get_device_diagnostics(
        hass,
        entry,
        devices[0],
    )
    assert device_diagnostics == diagnostics
    serialized = json.dumps(diagnostics, sort_keys=True)
    for sentinel in sentinels.values():
        assert sentinel not in serialized
        assert sentinel not in caplog.text
    assert diagnostics["policy"]["authority"] == "persistent"
    assert diagnostics["runtime"]["connection_generation"] >= 1
    assert diagnostics["availability"]["available_count"] > 0
    assert diagnostics["availability"]["error_count"] >= 0
    assert set(diagnostics["tiers"]) == {"fast", "slow", "static"}
