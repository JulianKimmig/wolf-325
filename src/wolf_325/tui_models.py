"""Pure presentation models shared by the Textual controller interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import RegisterError
from .register import RegisterDef


@dataclass(frozen=True, slots=True)
class RegisterRow:
    """Represent one register in the main value table."""

    key: str
    label: str
    value: str
    unit: str
    status: str
    flags: str
    updated: str


@dataclass(frozen=True, slots=True)
class EditorSpec:
    """Describe the appropriate write control and its safety constraints."""

    kind: str
    initial: str
    options: tuple[str, ...]
    persist_allowed: bool
    dangerous: bool
    one_shot: bool
    confirmation_phrase: str | None
    help_text: str


def _state_for(snapshot: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a state mapping for a key, preserving unavailable catalogue rows."""
    values = snapshot.get("values", {})
    state = values.get(key, {}) if isinstance(values, dict) else {}
    return state if isinstance(state, dict) else {}


def _format_value(value: Any) -> str:
    """Format a JSON-compatible engineering value compactly for a table cell."""
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def build_register_rows(
    keys: tuple[str, ...] | list[str],
    snapshot: dict[str, Any],
    *,
    desired: dict[str, Any] | None = None,
    search: str = "",
) -> list[RegisterRow]:
    """Build searchable table rows for canonical register keys.

    Args:
        keys: Canonical register keys to include before filtering.
        snapshot: Public controller snapshot containing value states.
        desired: Optional persistent desired-state mapping.
        search: Case-insensitive query matched across metadata and state.

    Returns:
        Ordered presentation rows matching the search query.
    """
    from .catalogue import REGISTERS

    owned = desired or {}
    query = search.strip().casefold()
    rows: list[RegisterRow] = []
    for key in keys:
        register = REGISTERS[key]
        state = _state_for(snapshot, key)
        error = state.get("error")
        available = bool(state.get("available"))
        flags = []
        if register.writable:
            flags.append("write")
        if key in owned:
            flags.append("desired")
        if register.dangerous:
            flags.append("danger")
        if register.one_shot:
            flags.append("action")
        status = "error" if error else "live" if available else "waiting"
        haystack = " ".join(
            (
                key,
                register.description,
                str(register.address),
                register.table,
                register.unit or "",
                status,
                str(error or ""),
                *flags,
            )
        ).casefold()
        if query and not all(token in haystack for token in query.split()):
            continue
        updated = str(state.get("updated_at") or "").replace("T", " ")[:19]
        rows.append(
            RegisterRow(
                key=key,
                label=register.description,
                value=_format_value(state.get("value")),
                unit=register.unit or "",
                status=status,
                flags=", ".join(flags) or "read",
                updated=updated or "never",
            )
        )
    return rows


def _allowed_text(register: RegisterDef) -> str:
    """Describe enum or numeric constraints in operator-facing language."""
    if register.enum:
        return "Allowed: " + ", ".join(register.enum.values())
    bounds: str
    if register.minimum is not None and register.maximum is not None:
        bounds = f"{register.minimum:g}–{register.maximum:g}"
    elif register.minimum is not None:
        bounds = f"≥ {register.minimum:g}"
    elif register.maximum is not None:
        bounds = f"≤ {register.maximum:g}"
    else:
        return "Allowed: validated by the register codec"
    unit = f" {register.unit}" if register.unit else ""
    step = f"; step {register.step:g}" if register.step is not None else ""
    extras = (
        "; special " + ", ".join(f"{value:g}" for value in register.extra_values)
        if register.extra_values
        else ""
    )
    return f"Allowed: {bounds}{unit}{step}{extras}"


def format_register_details(
    key: str,
    state: dict[str, Any],
    *,
    desired: Any = None,
    is_desired: bool = True,
) -> str:
    """Render complete register and runtime metadata for the detail panel.

    Args:
        key: Canonical register key.
        state: Public state mapping from a controller snapshot.
        desired: Desired value to display when the key is owned.
        is_desired: Whether ``desired`` represents persistent ownership.

    Returns:
        Multi-line plain-text register details.
    """
    from .catalogue import REGISTERS

    register = REGISTERS[key]
    table = "Holding" if register.table == "holding" else "Input"
    capability_labels = [
        label
        for enabled, label in (
            (register.writable, "writable"),
            (register.restorable, "persistent"),
            (register.dangerous, "dangerous"),
            (register.one_shot, "one-shot action"),
            (register.optional, "optional"),
        )
        if enabled
    ]
    capabilities = ", ".join(capability_labels) or "read-only"
    lines = [
        register.description,
        key,
        f"{table} register {register.address} · {register.count} word(s) · codec {register.codec}",
        f"Polling: {register.poll} · Unit: {register.unit or '—'}",
        _allowed_text(register),
        f"Capabilities: {capabilities}",
        f"Current value: {_format_value(state.get('value'))}",
        f"Raw value: {_format_value(state.get('raw'))}",
        f"Last update: {state.get('updated_at') or 'never'}",
    ]
    if is_desired:
        lines.append(f"Persistent desired value: {_format_value(desired)}")
    if state.get("error"):
        lines.append(f"Last error: {state['error']}")
    return "\n".join(lines)


def build_editor_spec(register: RegisterDef, current: Any) -> EditorSpec:
    """Derive the write editor type and guard requirements from metadata.

    Args:
        register: Canonical writable register definition.
        current: Current engineering value, or ``None`` when unavailable.

    Returns:
        Immutable editor specification for a modal screen.

    Raises:
        RegisterError: If the register is read-only.
    """
    if not register.writable:
        raise RegisterError(f"{register.key}: read-only value")
    options: tuple[str, ...] = ()
    kind = "number"
    if register.one_shot:
        kind = "action"
    elif register.enum:
        kind = "select"
        options = tuple(register.enum.values())
    elif register.codec in {"bool", "standby_command"}:
        kind = "select"
        options = ("false", "true")
    elif register.codec.startswith("packed_"):
        kind = "text"
    phrase = None
    if register.key == "appliance_reset_status":
        phrase = "RESET APPLIANCE"
    elif register.dangerous:
        phrase = "APPLY DANGEROUS WRITE"
    elif register.one_shot:
        phrase = "EXECUTE ACTION"
    help_text = _allowed_text(register)
    if register.dangerous:
        help_text += ". This write may disconnect or restart the device."
    return EditorSpec(
        kind=kind,
        initial="" if current is None else str(current).lower() if isinstance(current, bool) else str(current),
        options=options,
        persist_allowed=register.restorable and not register.one_shot,
        dangerous=register.dangerous,
        one_shot=register.one_shot,
        confirmation_phrase=phrase,
        help_text=help_text,
    )


def parse_editor_value(register: RegisterDef, text: str) -> Any:
    """Validate editor text with the canonical register codec.

    Args:
        register: Target canonical register definition.
        text: User-entered or selected value.

    Returns:
        Canonical JSON scalar accepted by the controller.

    Raises:
        ValueError: If canonical register validation rejects the text.
    """
    try:
        return register.normalize(text)
    except RegisterError as exc:
        raise ValueError(str(exc)) from exc


__all__ = [
    "EditorSpec",
    "RegisterRow",
    "build_editor_spec",
    "build_register_rows",
    "format_register_details",
    "parse_editor_value",
]
