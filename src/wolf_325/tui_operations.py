"""Interactive actions and asynchronous workers mixed into the Textual app."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from textual.widgets import DataTable, Input, RichLog

from .catalogue import REGISTERS
from .tui_dialogs import (
    ProfileDialog,
    ProfileRequest,
    RegisterEditor,
    SaveProfileDialog,
    SaveProfileRequest,
    WriteRequest,
)
from .tui_models import build_editor_spec


class TuiOperationsMixin:
    """Provide keyboard actions, dialogs, workers, and activity reporting."""

    def action_focus_search(self) -> None:
        """Focus the search input for immediate filtering."""
        self.query_one("#search", Input).focus()

    def action_focus_table(self) -> None:
        """Return keyboard focus to the register value table."""
        self.query_one("#register-table", DataTable).focus()

    def action_refresh_selected(self) -> None:
        """Start an immediate selected-register refresh worker."""
        self.run_worker(self._refresh_operation(), group="device", exclusive=True)

    def action_edit_selected(self) -> None:
        """Open the metadata-derived editor for the highlighted register."""
        key = self._selected_key
        if not key or self.read_only or not REGISTERS[key].writable:
            return
        state = self._snapshot.get("values", {}).get(key, {})
        current = state.get("value") if isinstance(state, dict) else None
        editor = RegisterEditor(
            REGISTERS[key], build_editor_spec(REGISTERS[key], current)
        )
        self.push_screen(editor, lambda request: self._accept_write(key, request))

    def action_release_desired(self) -> None:
        """Release highlighted desired-state ownership in a device worker."""
        if self._selected_key and not self.read_only:
            self.run_worker(
                self._release_operation(self._selected_key),
                group="device",
                exclusive=True,
            )

    def action_profiles(self) -> None:
        """Open the profile review modal when writes are enabled."""
        if not self.read_only:
            self.push_screen(ProfileDialog(self.service), self._accept_profile)

    def action_save_profile(self) -> None:
        """Open the derived-profile capture modal when writes are enabled."""
        if not self.read_only:
            self.push_screen(
                SaveProfileDialog(self.service), self._accept_save_profile
            )

    def action_apply_desired(self) -> None:
        """Force persistent desired state through the controller worker."""
        if not self.read_only:
            self.run_worker(
                self._apply_desired_operation(), group="device", exclusive=True
            )

    def _accept_write(self, key: str, request: WriteRequest | None) -> None:
        """Start a write worker for a confirmed register editor result.

        Args:
            key: Canonical target register key captured before opening the modal.
            request: Submitted request or ``None`` when the modal was cancelled.
        """
        if request:
            self.run_worker(
                self._write_operation(key, request), group="device", exclusive=True
            )

    def _accept_profile(self, request: ProfileRequest | None) -> None:
        """Start a profile worker for a reviewed modal result.

        Args:
            request: Submitted profile request, or ``None`` after cancellation.
        """
        if request:
            self.run_worker(
                self._profile_operation(request), group="device", exclusive=True
            )

    def _accept_save_profile(self, request: SaveProfileRequest | None) -> None:
        """Start a profile-save worker for a confirmed modal result.

        Args:
            request: Submitted capture request, or ``None`` after cancellation.
        """
        if request:
            self.run_worker(
                self._save_profile_operation(request),
                group="device",
                exclusive=True,
            )

    async def _execute(self, label: str, operation: Awaitable[Any]) -> Any:
        """Run an operation while synchronizing busy state and error reporting.

        Args:
            label: Operator-facing activity description.
            operation: Awaitable controller/service operation.

        Returns:
            Underlying operation result, or ``None`` after a reported failure.
        """
        self._busy = True
        self._select_key(self._selected_key)
        self._log(f"[cyan]{label}…[/cyan]")
        try:
            result = await operation
        except Exception as exc:
            self._log(f"[red]{label} failed:[/red] {exc}")
            self.notify(str(exc), title=f"{label} failed", severity="error")
            return None
        finally:
            self._busy = False
            self._refresh_snapshot()
            self._render_table()
        self._log(f"[green]{label} complete:[/green] {result}")
        self.notify(f"{label} complete", title="Controller")
        return result

    async def _refresh_operation(self) -> Any:
        """Refresh the selected register and surface its result."""
        return await self._execute(
            "Refresh selected",
            self.service.refresh(self._selected_key),
        )

    async def _write_operation(self, key: str, request: WriteRequest) -> Any:
        """Execute a confirmed write and refresh its register.

        Args:
            key: Canonical target register key.
            request: Validated editor request.
        """
        result = await self._execute(
            f"Write {key}",
            self.service.write_register(
                key,
                request.value,
                persist=request.persist,
                confirmation=request.confirmation,
            ),
        )
        if result is not None and not REGISTERS[key].one_shot:
            await self._execute(f"Refresh {key}", self.service.refresh(key))
        return result

    async def _release_operation(self, key: str) -> Any:
        """Release one persistent desired-state key.

        Args:
            key: Canonical desired-state key to release.
        """
        return await self._execute(
            f"Release {key}", self.service.release_desired(key)
        )

    async def _profile_operation(self, request: ProfileRequest) -> Any:
        """Apply a reviewed profile request.

        Args:
            request: Selected profile and persistence choice.
        """
        return await self._execute(
            f"Apply profile {request.name}",
            self.service.apply_profile(request.name, persist=request.persist),
        )

    async def _save_profile_operation(self, request: SaveProfileRequest) -> Any:
        """Save the current desired-state delta as a profile.

        Args:
            request: Profile name, description, and overwrite choice.
        """
        return await self._execute(
            f"Save profile {request.name}",
            self.service.save_profile(
                request.name,
                description=request.description,
                overwrite=request.overwrite,
            ),
        )

    async def _apply_desired_operation(self) -> Any:
        """Force the complete persistent desired state to the device."""
        return await self._execute("Apply desired state", self.service.apply_desired())

    def _log(self, message: str) -> None:
        """Append Rich markup to the on-screen activity history.

        Args:
            message: Rich-formatted activity message.
        """
        self.query_one("#activity-log", RichLog).write(message)


__all__ = ["TuiOperationsMixin"]
