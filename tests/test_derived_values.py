"""Behavior tests for virtual values derived from live air-stream measurements."""

from __future__ import annotations

import math

import pytest

from wolf_325 import WolfCWL2
from wolf_325.derived_values import calculate_dew_point_c

from conftest import FakeClient


@pytest.mark.parametrize(
    ("temperature_c", "relative_humidity_pct", "expected_c"),
    [
        (20.0, 50.0, 9.3),
        (26.5, 27.0, 6.0),
        (29.1, 33.0, 11.2),
        (-5.0, 100.0, -5.0),
    ],
)
def test_dew_point_calculation_uses_temperature_and_whole_percent_humidity(
    temperature_c: float, relative_humidity_pct: float, expected_c: float
) -> None:
    """Calculate one-decimal dew points across ordinary and freezing inputs."""
    assert calculate_dew_point_c(temperature_c, relative_humidity_pct) == expected_c


@pytest.mark.parametrize(
    ("temperature_c", "relative_humidity_pct"),
    [
        (20.0, 0.0),
        (20.0, -1.0),
        (20.0, 100.1),
        (-243.12, 50.0),
        (math.nan, 50.0),
        (20.0, math.inf),
    ],
)
def test_dew_point_calculation_rejects_invalid_measurements(
    temperature_c: float, relative_humidity_pct: float
) -> None:
    """Reject undefined humidity and non-finite dependency measurements."""
    with pytest.raises(ValueError):
        calculate_dew_point_c(temperature_c, relative_humidity_pct)


async def test_refreshing_virtual_dew_point_reads_dependencies(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Refresh both physical dependencies and expose one virtual state record."""
    instance, client = controller
    client.input[4036] = 265
    client.input[4037] = 27

    value = await instance.refresh("supply_dew_point_c")

    assert value == 6.0
    assert [(table, address, count) for table, address, count, _ in client.reads] == [
        ("input", 4036, 1),
        ("input", 4037, 1),
    ]
    assert instance.get_state("supply_dew_point_c") == {
        "value": 6.0,
        "raw": None,
        "unit": "°C",
        "available": True,
        "updated_at": instance.get_state("supply_dew_point_c")["updated_at"],
        "error": None,
    }


async def test_dependency_updates_recalculate_virtual_dew_point(
    controller: tuple[WolfCWL2, FakeClient],
) -> None:
    """Recalculate and emit the derived value after a humidity change."""
    instance, client = controller
    received: list[dict[str, object]] = []
    instance.subscribe(received.append)
    client.input[4046] = 291
    client.input[4047] = 33
    await instance.refresh("exhaust_dew_point_c")
    client.input[4047] = 40

    await instance.refresh("exhaust_relative_humidity_pct")

    assert instance.get_value("exhaust_dew_point_c") == 14.1
    assert [update["key"] for update in received][-2:] == [
        "exhaust_relative_humidity_pct",
        "exhaust_dew_point_c",
    ]
