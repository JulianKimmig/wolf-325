"""Modal write and profile dialogs for the controller TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, Switch

from .register import RegisterDef
from .tui_models import EditorSpec, parse_editor_value
from .tui_service import ControllerTuiService


@dataclass(frozen=True, slots=True)
class WriteRequest:
    """Represent a confirmed register editor submission."""

    value: str
    persist: bool
    confirmation: str | None


@dataclass(frozen=True, slots=True)
class ProfileRequest:
    """Represent a reviewed profile application request."""

    name: str
    persist: bool


@dataclass(frozen=True, slots=True)
class SaveProfileRequest:
    """Represent a request to persist current changes as a new profile."""

    name: str
    description: str
    overwrite: bool


class RegisterEditor(ModalScreen[WriteRequest | None]):
    """Edit one value using controls derived from canonical metadata."""

    def __init__(self, register: RegisterDef, spec: EditorSpec) -> None:
        """Initialize the register modal.

        Args:
            register: Canonical target register definition.
            spec: Derived control and confirmation specification.
        """
        super().__init__()
        self.register = register
        self.spec = spec

    def compose(self) -> ComposeResult:
        """Yield the value, persistence, confirmation, and action controls."""
        with Vertical(id="register-dialog", classes="dialog"):
            yield Label(self.register.description, classes="dialog-title")
            yield Static(f"{self.register.key}\n{self.spec.help_text}")
            if self.spec.kind == "select":
                options = [(item, item) for item in self.spec.options]
                initial = self.spec.initial if self.spec.initial in self.spec.options else Select.NULL
                yield Select(options, value=initial, allow_blank=False, id="editor-value")
            elif self.spec.kind != "action":
                yield Input(value=self.spec.initial, id="editor-input")
            if self.spec.persist_allowed:
                with Horizontal(classes="field-row"):
                    yield Label("Persist and reconcile")
                    yield Switch(value=True, id="editor-persist")
            if self.spec.confirmation_phrase:
                yield Label(f"Type exactly: {self.spec.confirmation_phrase}", classes="warning")
                yield Input(placeholder=self.spec.confirmation_phrase, id="editor-confirm")
            yield Static("", id="editor-error", classes="error")
            with Horizontal(classes="dialog-actions"):
                yield Button("Cancel", id="cancel")
                label = "Execute" if self.spec.kind == "action" else "Write"
                yield Button(label, id="submit", variant="warning" if self.spec.dangerous else "primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Validate controls and dismiss with a request or cancellation."""
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        value = ""
        if self.spec.kind == "select":
            value = str(self.query_one("#editor-value", Select).value)
        elif self.spec.kind != "action":
            value = self.query_one("#editor-input", Input).value
        try:
            if self.spec.kind != "action":
                parse_editor_value(self.register, value)
        except ValueError as exc:
            self.query_one("#editor-error", Static).update(str(exc))
            return
        confirmation = None
        if self.spec.confirmation_phrase:
            confirmation = self.query_one("#editor-confirm", Input).value
            if confirmation != self.spec.confirmation_phrase:
                self.query_one("#editor-error", Static).update("Confirmation phrase does not match.")
                return
        persist = (
            self.query_one("#editor-persist", Switch).value
            if self.spec.persist_allowed
            else False
        )
        self.dismiss(WriteRequest(value, persist, confirmation))


class ProfileDialog(ModalScreen[ProfileRequest | None]):
    """List, preview, and request application of configured profiles."""

    def __init__(self, service: ControllerTuiService) -> None:
        """Initialize a profile dialog backed by the TUI service."""
        super().__init__()
        self.service = service

    def compose(self) -> ComposeResult:
        """Yield profile selection, preview, persistence, and action controls."""
        with Vertical(id="profile-dialog", classes="dialog"):
            yield Label("Profiles", classes="dialog-title")
            yield Select([], prompt="Loading profiles…", id="profile-select")
            yield Static("Select a profile to inspect its resolved effects.", id="profile-preview")
            with Horizontal(classes="field-row"):
                yield Label("Persist as desired state")
                yield Switch(value=True, id="profile-persist")
            yield Static("", id="profile-error", classes="error")
            with Horizontal(classes="dialog-actions"):
                yield Button("Cancel", id="profile-cancel")
                yield Button("Apply profile", id="profile-apply", variant="primary", disabled=True)

    async def on_mount(self) -> None:
        """Load profile names after the modal is attached to the application."""
        try:
            names = await self.service.list_profiles()
        except Exception as exc:
            self.query_one("#profile-error", Static).update(str(exc))
            return
        select = self.query_one("#profile-select", Select)
        select.set_options((name, name) for name in names)
        select.prompt = "Select a profile" if names else "No profiles configured"

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Render the fully resolved profile when selection changes."""
        if event.select.id != "profile-select" or event.value is Select.NULL:
            return
        name = str(event.value)
        try:
            preview = await self.service.preview_profile(name)
        except Exception as exc:
            self.query_one("#profile-error", Static).update(str(exc))
            return
        self.query_one("#profile-preview", Static).update(preview)
        self.query_one("#profile-apply", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss with the selected request or cancel without side effects."""
        if event.button.id == "profile-cancel":
            self.dismiss(None)
            return
        select = self.query_one("#profile-select", Select)
        if select.value is Select.NULL:
            return
        persist = self.query_one("#profile-persist", Switch).value
        self.dismiss(ProfileRequest(str(select.value), persist))


class SaveProfileDialog(ModalScreen[SaveProfileRequest | None]):
    """Preview and save persistent desired changes as a derived profile."""

    def __init__(self, service: ControllerTuiService) -> None:
        """Initialize a capture dialog backed by the controller TUI service.

        Args:
            service: Safety-aware service used to preview the current delta.
        """
        super().__init__()
        self.service = service

    def compose(self) -> ComposeResult:
        """Yield delta preview, profile metadata, overwrite, and action controls."""
        with Vertical(id="save-profile-dialog", classes="dialog"):
            yield Label("Save current changes", classes="dialog-title")
            yield Static(
                "Loading persistent desired-state changes…",
                id="save-profile-preview",
            )
            yield Label("New profile name")
            yield Input(placeholder="example: custom-night", id="profile-name")
            yield Label("Description")
            yield Input(
                placeholder="What is different about this profile?",
                id="profile-description",
            )
            with Horizontal(classes="field-row"):
                yield Label("Overwrite existing profile")
                yield Switch(value=False, id="profile-overwrite")
            yield Static("", id="save-profile-error", classes="error")
            with Horizontal(classes="dialog-actions"):
                yield Button("Cancel", id="save-profile-cancel")
                yield Button(
                    "Save profile",
                    id="save-profile-submit",
                    variant="primary",
                )

    async def on_mount(self) -> None:
        """Load the current derived-profile delta into the preview panel."""
        try:
            preview = await self.service.preview_profile_capture()
        except Exception as exc:
            self.query_one("#save-profile-error", Static).update(str(exc))
            self.query_one("#save-profile-submit", Button).disabled = True
            return
        self.query_one("#save-profile-preview", Static).update(preview)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Validate required metadata and dismiss with a save request."""
        if event.button.id == "save-profile-cancel":
            self.dismiss(None)
            return
        name = self.query_one("#profile-name", Input).value.strip()
        if not name:
            self.query_one("#save-profile-error", Static).update(
                "Profile name is required."
            )
            return
        description = self.query_one("#profile-description", Input).value.strip()
        overwrite = self.query_one("#profile-overwrite", Switch).value
        self.dismiss(SaveProfileRequest(name, description, overwrite))


__all__ = [
    "ProfileDialog",
    "ProfileRequest",
    "RegisterEditor",
    "SaveProfileDialog",
    "SaveProfileRequest",
    "WriteRequest",
]
