"""Behavior tests for safe live-context validation of related settings."""

from __future__ import annotations

import pytest

from wolf_325 import REGISTERS, ValidationError, WolfCWL2

from conftest import FakeClient


def _set_confirmed_airflow_presets(client: FakeClient) -> None:
    """Populate one valid confirmed airflow preset sequence."""
    values = {
        "flow_preset_holiday_m3h": 100,
        "flow_preset_low_m3h": 150,
        "flow_preset_normal_m3h": 200,
        "flow_preset_high_m3h": 250,
    }
    for key, value in values.items():
        client.holding[REGISTERS[key].address] = value


async def test_temporary_relational_write_uses_fresh_confirmed_peers(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A one-key temporary change cannot violate the live preset sequence."""
    instance, client = controller
    _set_confirmed_airflow_presets(client)

    with pytest.raises(ValidationError, match="airflow presets"):
        await instance.set_setting(
            "flow_preset_low_m3h", 225, persist=False
        )

    assert client.writes == []
    assert {
        address for table, address, _count, _device_id in client.reads
        if table == "holding"
    } >= {
        REGISTERS["flow_preset_holiday_m3h"].address,
        REGISTERS["flow_preset_normal_m3h"].address,
        REGISTERS["flow_preset_high_m3h"].address,
    }


async def test_relational_preflight_fails_before_persistent_mutation(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """An invalid live candidate changes neither desired state nor the appliance."""
    instance, client = controller
    _set_confirmed_airflow_presets(client)
    before = instance.desired

    with pytest.raises(ValidationError, match="airflow presets"):
        await instance.set_setting(
            "flow_preset_normal_m3h", 275, persist=True
        )

    assert instance.desired == before
    assert client.writes == []


async def test_complete_relational_bundle_does_not_need_peer_reads(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """A complete valid bundle can validate coherently without stale peers."""
    instance, client = controller

    await instance.set_flow_presets(
        holiday=100,
        low=150,
        normal=200,
        high=250,
        persist=False,
    )

    assert len(client.reads) == 4
    assert {address for _table, address, _count, _device_id in client.reads} == {
        REGISTERS[key].address
        for key in (
            "flow_preset_holiday_m3h",
            "flow_preset_low_m3h",
            "flow_preset_normal_m3h",
            "flow_preset_high_m3h",
        )
    }
    assert len(client.writes) == 4
