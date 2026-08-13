"""Domain taxonomy used to navigate the complete controller catalogue."""

from __future__ import annotations

from dataclasses import dataclass

from .catalogue import REGISTERS


@dataclass(frozen=True, slots=True)
class RegisterSection:
    """Describe one leaf submenu containing related canonical registers.

    Attributes:
        section_id: Stable identifier used by UI events and tests.
        parent: Top-level menu identifier, either monitor or settings.
        title: Human-readable submenu label.
        description: Short operational explanation shown above its values.
        register_keys: Canonical register keys in Modbus address order.
        dangerous: Whether the section contains disconnecting or reset writes.
    """

    section_id: str
    parent: str
    title: str
    description: str
    register_keys: tuple[str, ...]
    dangerous: bool = False


@dataclass(frozen=True, slots=True)
class _RangeSection:
    """Define section metadata and an inclusive address interval."""

    section_id: str
    parent: str
    title: str
    description: str
    start: int
    end: int
    dangerous: bool = False


_RANGES = (
    _RangeSection("identity", "monitor", "Device identity", "Base controller identity and firmware.", 4000, 4019),
    _RangeSection("operation", "monitor", "Operating mode", "Active function, mode, control type, and pressures.", 4020, 4029),
    _RangeSection("live-airflow", "monitor", "Live airflow & fans", "Supply and exhaust targets, actual flow, speed, and climate.", 4030, 4049),
    _RangeSection("protection", "monitor", "Bypass, heater & frost", "Heat recovery bypass, preheater, and frost-protection state.", 4050, 4079),
    _RangeSection("local-io", "monitor", "Local sensors & I/O", "Physical controls, temperatures, humidity, and outputs.", 4080, 4109),
    _RangeSection("runtime", "monitor", "Clock, runtime & filters", "Device clock and accumulated operating/filter counters.", 4110, 4199),
    _RangeSection("co2-live", "monitor", "CO₂ sensors", "Status and measured concentration for all CO₂ sensors.", 4200, 4399),
    _RangeSection("display", "monitor", "Display module", "Local UI hardware, firmware, switch, and button state.", 4400, 4499),
    _RangeSection("extension", "monitor", "Extension module", "UWA2-E identity, contacts, analogue channels, and relays.", 4500, 4599),
    _RangeSection("airflow-presets", "settings", "Airflow presets", "Holiday, low, normal, and high airflow targets.", 6000, 6009),
    _RangeSection("pwm-presets", "settings", "PWM presets", "Supply and exhaust PWM for each ventilation level.", 6010, 6029),
    _RangeSection("fan-control", "settings", "Fan control & balance", "Control method, physical switch behavior, and fan balance.", 6030, 6099),
    _RangeSection("bypass-settings", "settings", "Bypass & frost", "Bypass thresholds, boost, and frost-control limits.", 6100, 6119),
    _RangeSection("filter-heating", "settings", "Filter & heating", "Filter interval and external heater configuration.", 6120, 6139),
    _RangeSection("air-quality", "settings", "Humidity & CO₂", "Humidity control and CO₂ thresholds for every sensor.", 6140, 6169),
    _RangeSection("outputs", "settings", "Signal outputs", "24 V signal and central-heating exhaust integration.", 6170, 6199),
    _RangeSection("digital-inputs", "settings", "Digital inputs", "Contact type and fan behavior for both digital inputs.", 6200, 6219),
    _RangeSection("analog-inputs", "settings", "Analogue inputs", "Enable and calibrate both 0–10 V input channels.", 6220, 6239),
    _RangeSection("ground-exchanger", "settings", "Ground heat exchanger", "Ground exchanger thresholds, valve default, and output.", 6240, 6899),
    _RangeSection("display-clock", "settings", "Language, date & time", "Display language and appliance clock settings.", 6900, 7989),
    _RangeSection("communication", "settings", "Modbus communication", "Interface, address, and speed; writes may disconnect.", 7990, 7999, True),
    _RangeSection("remote-control", "settings", "Remote control", "Control mode, level, direct airflow target, and standby.", 8000, 8009),
    _RangeSection("actions", "settings", "Maintenance actions", "Filter warning and guarded appliance reset commands.", 8010, 8099, True),
)


def _build_sections() -> tuple[RegisterSection, ...]:
    """Build immutable register sections from catalogue address ranges.

    Returns:
        Complete ordered leaf sections with register membership resolved.

    Raises:
        RuntimeError: If any register is unassigned or assigned more than once.
    """
    sections: list[RegisterSection] = []
    memberships: dict[str, int] = {key: 0 for key in REGISTERS}
    for spec in _RANGES:
        keys = tuple(
            key
            for key, register in sorted(
                REGISTERS.items(), key=lambda item: (item[1].table, item[1].address)
            )
            if spec.start <= register.address <= spec.end
        )
        for key in keys:
            memberships[key] += 1
        sections.append(
            RegisterSection(
                spec.section_id,
                spec.parent,
                spec.title,
                spec.description,
                keys,
                spec.dangerous,
            )
        )
    invalid = {key: count for key, count in memberships.items() if count != 1}
    if invalid:
        raise RuntimeError(f"TUI register taxonomy is incomplete: {invalid}")
    return tuple(sections)


REGISTER_SECTIONS = _build_sections()
"""All domain leaf sections in their displayed order."""


def section_by_id(section_id: str) -> RegisterSection:
    """Return one section by stable identifier.

    Args:
        section_id: Stable section identifier from :data:`REGISTER_SECTIONS`.

    Returns:
        Matching register section.

    Raises:
        KeyError: If no section has the requested identifier.
    """
    for section in REGISTER_SECTIONS:
        if section.section_id == section_id:
            return section
    raise KeyError(section_id)


__all__ = ["REGISTER_SECTIONS", "RegisterSection", "section_by_id"]
