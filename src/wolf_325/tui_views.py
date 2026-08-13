"""View resolution and tree construction for the controller TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.widgets import Tree

from .catalogue import REGISTERS
from .tui_navigation import REGISTER_SECTIONS, section_by_id


OVERVIEW_KEYS = (
    "active_function",
    "ventilation_mode",
    "supply_airflow_setpoint_m3h",
    "supply_airflow_actual_m3h",
    "exhaust_airflow_setpoint_m3h",
    "exhaust_airflow_actual_m3h",
    "supply_fan_speed_rpm",
    "exhaust_fan_speed_rpm",
    "supply_temperature_c",
    "exhaust_temperature_c",
    "exhaust_relative_humidity_pct",
    "bypass_status",
    "frost_status",
    "filter_status",
    "co2_sensor_1_ppm",
    "remote_control_mode",
    "remote_ventilation_level",
    "remote_airflow_m3h",
    "remote_standby",
)
"""High-signal live and control values shown on the opening dashboard."""


@dataclass(frozen=True, slots=True)
class ResolvedView:
    """Describe a selected view and its current register keys."""

    title: str
    description: str
    register_keys: tuple[str, ...]


def _catalogue_order() -> tuple[str, ...]:
    """Return every key in input/holding address order."""
    return tuple(
        key
        for key, _ in sorted(
            REGISTERS.items(), key=lambda item: (item[1].table, item[1].address)
        )
    )


ALL_KEYS = _catalogue_order()
"""Complete stable catalogue ordering used by broad views."""


def resolve_view(
    view_id: str, snapshot: dict[str, Any], desired: dict[str, Any]
) -> ResolvedView:
    """Resolve a stable view identifier against current runtime state.

    Args:
        view_id: Special view identifier or ``section:<section-id>``.
        snapshot: Complete controller snapshot used for problem filtering.
        desired: Current persistent desired-state mapping.

    Returns:
        Human-readable title, description, and ordered register keys.

    Raises:
        KeyError: If the view identifier is unknown.
    """
    if view_id.startswith("section:"):
        section = section_by_id(view_id.removeprefix("section:"))
        return ResolvedView(section.title, section.description, section.register_keys)
    if view_id == "overview":
        return ResolvedView("Overview", "High-signal live operation and remote-control values.", OVERVIEW_KEYS)
    if view_id == "all":
        return ResolvedView("All registers", "Every documented value in Modbus address order.", ALL_KEYS)
    if view_id == "writable":
        keys = tuple(key for key in ALL_KEYS if REGISTERS[key].writable)
        return ResolvedView("Writable registers", "Every setting and guarded action exposed by the device.", keys)
    if view_id == "desired":
        keys = tuple(key for key in ALL_KEYS if key in desired)
        return ResolvedView("Desired state", "Persistent settings owned and reconciled by this controller.", keys)
    if view_id == "problems":
        values = snapshot.get("values", {})
        keys = tuple(
            key
            for key in ALL_KEYS
            if isinstance(values, dict)
            and isinstance(values.get(key), dict)
            and values[key].get("error")
        )
        return ResolvedView("Problems", "Registers whose most recent read or decode failed.", keys)
    raise KeyError(view_id)


def populate_navigation(tree: Tree[str]) -> None:
    """Populate top-level quick views and domain submenus into a tree.

    Args:
        tree: Empty Textual tree whose node data stores stable view identifiers.
    """
    tree.root.data = "overview"
    quick = tree.root.add("Quick views", expand=True)
    for title, view_id in (
        ("Overview", "overview"),
        ("All registers", "all"),
        ("Writable", "writable"),
        ("Problems", "problems"),
    ):
        quick.add_leaf(title, view_id)
    for parent, title in (("monitor", "Monitor"), ("settings", "Settings")):
        node = tree.root.add(title, expand=True)
        for section in REGISTER_SECTIONS:
            if section.parent == parent:
                label = f"⚠ {section.title}" if section.dangerous else section.title
                node.add_leaf(label, f"section:{section.section_id}")
    ownership = tree.root.add("Ownership & profiles", expand=True)
    ownership.add_leaf("Desired state", "desired")
    tree.root.expand()


__all__ = ["ALL_KEYS", "OVERVIEW_KEYS", "ResolvedView", "populate_navigation", "resolve_view"]
