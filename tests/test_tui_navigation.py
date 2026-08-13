"""Behavior tests for complete, domain-oriented TUI navigation."""

from __future__ import annotations

from collections import Counter

from wolf_325.catalogue import REGISTERS
from wolf_325.tui_navigation import REGISTER_SECTIONS, section_by_id


def test_register_sections_partition_the_complete_catalogue_once() -> None:
    """Every canonical register appears in one and only one domain submenu."""
    memberships = Counter(
        key for section in REGISTER_SECTIONS for key in section.register_keys
    )

    assert set(memberships) == set(REGISTERS)
    assert set(memberships.values()) == {1}


def test_navigation_exposes_monitor_and_settings_submenus() -> None:
    """The taxonomy separates live monitoring from configurable domains."""
    parents = {section.parent for section in REGISTER_SECTIONS}

    assert parents == {"monitor", "settings"}
    assert section_by_id("live-airflow").title == "Live airflow & fans"
    assert section_by_id("remote-control").title == "Remote control"
    assert section_by_id("communication").dangerous is True
    assert section_by_id("actions").dangerous is True


def test_register_order_follows_table_then_modbus_address() -> None:
    """Rows in each domain remain stable and meaningful to device operators."""
    for section in REGISTER_SECTIONS:
        order = [
            (REGISTERS[key].table, REGISTERS[key].address)
            for key in section.register_keys
        ]
        assert order == sorted(order)
