"""Textual application for comprehensive WOLF controller monitoring and control."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    Tree,
)

from .catalogue import REGISTERS
from .controller import WolfCWL2
from .tui_models import build_register_rows, format_register_details
from .tui_operations import TuiOperationsMixin
from .tui_service import ControllerTuiService
from .tui_views import populate_navigation, resolve_view


class WolfCWL2App(TuiOperationsMixin, App[None]):
    """Monitor and operate every documented CWL-2 register in a terminal."""

    CSS_PATH = "tui.tcss"
    TITLE = "WOLF CWL-2 Controller"
    SUB_TITLE = "live Modbus monitor and settings console"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("slash", "focus_search", "Search"),
        ("r", "refresh_selected", "Refresh"),
        ("e", "edit_selected", "Edit"),
        ("p", "profiles", "Profiles"),
        ("s", "save_profile", "Save profile"),
        ("escape", "focus_table", "Values"),
    ]

    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        controller: WolfCWL2 | None = None,
        read_only: bool = False,
        refresh_interval: float = 1.0,
        background: bool = True,
    ) -> None:
        """Initialize the application and controller adapter.

        Args:
            config_path: Controller JSON path when no controller is injected.
            controller: Optional existing controller, primarily for integration.
            read_only: Whether all modifying UI controls must remain disabled.
            refresh_interval: Seconds between snapshot-to-table redraws.
            background: Whether controller polling tasks run after initial poll.

        Raises:
            ValueError: If neither a controller nor configuration path is given.
        """
        super().__init__()
        if controller is None:
            if config_path is None:
                raise ValueError("config_path is required when controller is absent")
            controller = WolfCWL2(config_path)
        self.service = ControllerTuiService(controller, read_only=read_only)
        self.read_only = read_only
        self.refresh_interval = refresh_interval
        self.background = background
        self._snapshot: dict[str, Any] = {"values": {}, "desired": {}}
        self._current_view = "overview"
        self._selected_key: str | None = None
        self._visible_keys: tuple[str, ...] = ()
        self._busy = False
        self._redraw_timer: Timer | None = None

    @property
    def visible_register_keys(self) -> tuple[str, ...]:
        """Return canonical keys currently visible after view/search filtering."""
        return self._visible_keys

    def compose(self) -> ComposeResult:
        """Yield the navigation, values, details, controls, status, and footer."""
        yield Header()
        with Horizontal(id="main-grid"):
            yield Tree("Controller", id="navigation")
            with Vertical(id="value-pane"):
                yield Input(placeholder="Search key, description, address, status, or error…", id="search")
                yield Static("Overview", id="view-title", markup=False)
                yield DataTable(id="register-table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="detail-pane"):
                yield Static("REGISTER DETAILS", id="detail-title")
                yield Static("Select a register to inspect it.", id="register-details", markup=False)
                with Vertical(id="toolbar"):
                    yield Button("Refresh", id="refresh")
                    yield Button("Edit / execute", id="edit", variant="primary", disabled=True)
                    yield Button("Release desired", id="release", disabled=True)
                    yield Button("Profiles", id="profiles", disabled=self.read_only)
                    yield Button(
                        "Save profile", id="save-profile", disabled=self.read_only
                    )
                    yield Button("Apply desired", id="apply-desired", disabled=self.read_only)
                yield RichLog(id="activity-log", wrap=True, highlight=True, markup=True)
        yield Static("Starting controller…", id="connection-status", markup=False)
        yield Footer()

    async def on_mount(self) -> None:
        """Build widgets, start the controller, and begin periodic redraws."""
        table = self.query_one("#register-table", DataTable)
        table.add_columns("Register", "Value", "Unit", "State", "Flags", "Updated")
        populate_navigation(self.query_one("#navigation", Tree))
        await self.service.start(background=self.background)
        self._log("[green]Controller initialized[/green]")
        self._refresh_snapshot()
        self._render_table()
        self._redraw_timer = self.set_interval(self.refresh_interval, self._tick)

    async def on_unmount(self) -> None:
        """Stop the controller cleanly when Textual removes the application."""
        if self._redraw_timer is not None:
            self._redraw_timer.stop()
        await self.service.stop()

    def _tick(self) -> None:
        """Copy controller state only while every redraw widget remains mounted.

        Returns:
            None after redrawing, or immediately for a queued teardown tick.
        """
        if not self._redraw_widgets_available():
            return
        self._refresh_snapshot()
        self._render_table()

    def _redraw_widgets_available(self) -> bool:
        """Return whether a queued tick can safely query every required widget.

        Returns:
            True only while the screen and all widgets used by redraw remain.
        """
        if not self.screen_stack or not self.screen.is_mounted:
            return False
        selectors = (
            "#connection-status",
            "#search",
            "#register-table",
            "#register-details",
            "#edit",
            "#release",
        )
        return all(len(self.query(selector)) == 1 for selector in selectors)

    def _refresh_snapshot(self) -> None:
        """Fetch one isolated snapshot and update the connection status line."""
        self._snapshot = self.service.snapshot()
        connected = bool(self._snapshot.get("connected"))
        state = "Connected" if connected else "Disconnected"
        mode = "READ ONLY" if self.read_only else "CONTROL ENABLED"
        generation = self._snapshot.get("connection_generation", 0)
        polls = self._snapshot.get("last_poll_at", {})
        fast = polls.get("fast") if isinstance(polls, dict) else None
        error = self._snapshot.get("last_connection_error")
        text = f"{state} · {mode} · generation {generation} · fast poll {fast or 'never'}"
        if error:
            text += f" · {error}"
        self.query_one("#connection-status", Static).update(text)

    def _keys_for_view(self) -> tuple[str, ...]:
        """Resolve the selected view against current snapshot and desired state."""
        desired = self._snapshot.get("desired", {})
        if not isinstance(desired, dict):
            desired = {}
        return resolve_view(self._current_view, self._snapshot, desired).register_keys

    def _render_table(self) -> None:
        """Rebuild filtered rows and synchronize details and button safety state."""
        desired = self._snapshot.get("desired", {})
        if not isinstance(desired, dict):
            desired = {}
        search = self.query_one("#search", Input).value
        rows = build_register_rows(
            self._keys_for_view(), self._snapshot, desired=desired, search=search
        )
        table = self.query_one("#register-table", DataTable)
        previous = self._selected_key
        table.clear(columns=False)
        for row in rows:
            table.add_row(
                row.label,
                row.value,
                row.unit,
                row.status,
                row.flags,
                row.updated,
                key=row.key,
            )
        self._visible_keys = tuple(row.key for row in rows)
        if previous in self._visible_keys:
            table.move_cursor(row=self._visible_keys.index(previous))
            self._select_key(previous)
        elif self._visible_keys:
            table.move_cursor(row=0)
            self._select_key(self._visible_keys[0])
        else:
            self._select_key(None)

    def _select_key(self, key: str | None) -> None:
        """Update details and modifying controls for one canonical key."""
        self._selected_key = key
        details = self.query_one("#register-details", Static)
        edit = self.query_one("#edit", Button)
        release = self.query_one("#release", Button)
        if key is None:
            details.update("No registers match this view and search.")
            edit.disabled = True
            release.disabled = True
            return
        values = self._snapshot.get("values", {})
        state = values.get(key, {}) if isinstance(values, dict) else {}
        desired = self._snapshot.get("desired", {})
        owned = isinstance(desired, dict) and key in desired
        desired_value = desired.get(key) if owned else None
        details.update(
            format_register_details(
                key, state if isinstance(state, dict) else {}, desired=desired_value, is_desired=owned
            )
        )
        edit.disabled = self.read_only or self._busy or not REGISTERS[key].writable
        release.disabled = self.read_only or self._busy or not owned

    async def show_view(self, view_id: str) -> None:
        """Select a special/domain view and immediately redraw its values.

        Args:
            view_id: Stable view identifier accepted by ``resolve_view``.
        """
        view = resolve_view(view_id, self._snapshot, self.service.controller.desired)
        self._current_view = view_id
        self.query_one("#search", Input).value = ""
        self.query_one("#view-title", Static).update(
            f"{view.title}\n{view.description}"
        )
        self._render_table()

    async def on_tree_node_selected(self, event: Tree.NodeSelected[str]) -> None:
        """Open a view when an operator activates a populated tree node."""
        if event.node.data:
            await self.show_view(event.node.data)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Apply search filtering as the operator types."""
        if event.input.id == "search":
            self._render_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Synchronize details with the highlighted table row."""
        if event.data_table.id == "register-table" and event.row_key.value:
            self._select_key(str(event.row_key.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch toolbar controls to their matching application actions."""
        actions = {
            "refresh": self.action_refresh_selected,
            "edit": self.action_edit_selected,
            "release": self.action_release_desired,
            "profiles": self.action_profiles,
            "save-profile": self.action_save_profile,
            "apply-desired": self.action_apply_desired,
        }
        action = actions.get(event.button.id or "")
        if action:
            action()

__all__ = ["WolfCWL2App"]
