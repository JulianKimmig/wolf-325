"""Safety-aware adapter between Textual screens and the public controller API."""

from __future__ import annotations

from typing import Any

from .catalogue import REGISTERS, resolve_register_name
from .controller import WolfCWL2
from .errors import RegisterError
from .profiles import SavedProfile
from .tui_models import build_editor_spec, parse_editor_value


class ControllerTuiService:
    """Execute TUI operations exclusively through supported controller methods."""

    def __init__(self, controller: WolfCWL2, *, read_only: bool) -> None:
        """Initialize an operation service.

        Args:
            controller: Controller instance whose lifecycle the TUI owns.
            read_only: Whether every device/config mutation must be rejected.
        """
        self.controller = controller
        self.read_only = read_only

    async def start(self, *, background: bool) -> None:
        """Load, poll, and optionally start controller background tasks.

        Args:
            background: Whether periodic controller polling should continue.
        """
        await self.controller.start(
            restore=False,
            background=background,
            read_only=self.read_only,
        )

    async def stop(self) -> None:
        """Stop polling, close transport, and persist the final state snapshot."""
        await self.controller.stop()

    def snapshot(self) -> dict[str, Any]:
        """Return the controller's complete public snapshot.

        Returns:
            Isolated snapshot containing connection, desired, and register state.
        """
        return self.controller.snapshot()

    async def refresh(self, key: str | None = None) -> None:
        """Refresh one selected register or all configured polling tiers.

        Args:
            key: Canonical/aliased key, or ``None`` to poll all tiers once.
        """
        if key is None:
            await self.controller.poll_once()
        else:
            await self.controller.refresh(key)

    async def write_register(
        self,
        key: str,
        text: str,
        *,
        persist: bool,
        confirmation: str | None,
    ) -> Any:
        """Validate and execute one normal or one-shot register write.

        Args:
            key: Canonical or aliased writable register name.
            text: Raw editor text; ignored for one-shot actions.
            persist: Whether restorable desired-state ownership is requested.
            confirmation: Exact safety phrase entered by the operator.

        Returns:
            Controller result or action status.

        Raises:
            RegisterError: If read-only, read-only register, or guard mismatch.
            ValueError: If canonical value validation rejects the editor text.
        """
        if self.read_only:
            raise RegisterError("TUI is in read-only mode")
        canonical = resolve_register_name(key)
        register = REGISTERS[canonical]
        spec = build_editor_spec(register, None)
        if spec.confirmation_phrase and confirmation != spec.confirmation_phrase:
            raise RegisterError(
                f"{canonical} requires confirmation phrase "
                f"{spec.confirmation_phrase!r}"
            )
        if register.one_shot:
            if canonical == "filter_reset_status":
                return await self.controller.reset_filter_warning()
            if canonical == "appliance_reset_status":
                return await self.controller.reset_appliance(confirm=True)
            raise RegisterError(f"unsupported one-shot action {canonical}")
        value = parse_editor_value(register, text)
        return await self.controller.set_setting(
            canonical,
            value,
            persist=persist,
            allow_dangerous=register.dangerous,
        )

    async def release_desired(self, key: str) -> None:
        """Release persistent ownership of one desired-state key.

        Args:
            key: Canonical or aliased register name to remove from desired state.
        """
        if self.read_only:
            raise RegisterError("TUI is in read-only mode")
        canonical = resolve_register_name(key)
        if canonical not in self.controller.desired:
            raise RegisterError(f"{canonical} is not owned by desired state")
        await self.controller.set_settings({}, persist=True, unset=(canonical,))

    async def apply_desired(self) -> dict[str, dict[str, Any]]:
        """Force all persistent desired settings to the device.

        Returns:
            Written, skipped, and failed desired-state mappings.
        """
        if self.read_only:
            raise RegisterError("TUI is in read-only mode")
        return await self.controller.apply_desired(force=True)

    async def list_profiles(self) -> list[str]:
        """Return all configured profile names in deterministic order."""
        return await self.controller.list_profiles()

    async def preview_profile(self, name: str) -> str:
        """Render a resolved profile for review before applying it.

        Args:
            name: Configured profile name.

        Returns:
            Multi-line description of inheritance, release, and setting effects.
        """
        profile = await self.controller.preview_profile(name)
        lines = [
            profile.description or "No description",
            f"Sources: {', '.join(profile.sources)}",
            f"Replace desired state: {'yes' if profile.replace else 'no'}",
        ]
        if profile.unset:
            lines.append("Release: " + ", ".join(profile.unset))
        lines.extend(f"{key} = {value}" for key, value in profile.settings.items())
        return "\n".join(lines)

    async def apply_profile(self, name: str, *, persist: bool) -> dict[str, Any]:
        """Apply a reviewed profile through the public controller API.

        Args:
            name: Configured profile name.
            persist: Whether profile settings become persistent desired state.

        Returns:
            Per-register controller results.
        """
        if self.read_only:
            raise RegisterError("TUI is in read-only mode")
        return await self.controller.apply_profile(name, persist=persist)

    async def preview_profile_capture(self) -> str:
        """Render persistent desired changes relative to the loaded profile.

        Returns:
            Multi-line base, replacement, setting, and release summary.
        """
        changes = await self.controller.preview_profile_changes()
        lines = [
            f"Base profile: {changes.extends or 'none (standalone)'}",
            f"Replace desired state: {'yes' if changes.replace else 'no'}",
            "Persistent changes:",
        ]
        if changes.settings:
            lines.extend(
                f"  {key} = {value}" for key, value in changes.settings.items()
            )
        else:
            lines.append("  none")
        lines.append("Released parent settings:")
        lines.extend(f"  {key}" for key in changes.unset)
        if not changes.unset:
            lines.append("  none")
        return "\n".join(lines)

    async def save_profile(
        self,
        name: str,
        *,
        description: str,
        overwrite: bool,
    ) -> SavedProfile:
        """Save current persistent changes through the controller API.

        Args:
            name: New profile name without a JSON extension.
            description: Operator-provided profile description.
            overwrite: Whether an existing profile may be replaced.

        Returns:
            Metadata for the atomically saved profile.

        Raises:
            RegisterError: If the TUI is operating in read-only mode.
        """
        if self.read_only:
            raise RegisterError("TUI is in read-only mode")
        return await self.controller.save_profile(
            name,
            description=description,
            overwrite=overwrite,
        )


__all__ = ["ControllerTuiService"]
