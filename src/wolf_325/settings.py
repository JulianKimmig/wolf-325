"""Public settings, profiles, resets, and desired-state reconciliation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .catalogue import REGISTERS, resolve_register_name
from .errors import (
    BulkWriteError,
    CommunicationError,
    RegisterError,
    WolfError,
)
from .profiles import ResolvedProfile
from .setting_relations import validate_live_relations
from .types import JSONValue
from .validation import normalize_settings, validate_cross_settings


class SettingsMixin:
    """Provide the high-level named write API to the controller."""

    async def set_setting(
        self,
        name: str,
        value: Any,
        *,
        persist: bool = True,
        verify: bool | None = None,
        allow_dangerous: bool = False,
    ) -> JSONValue | None:
        """Set one named value using bulk semantics and return its result."""
        result = await self.set_settings(
            {name: value},
            persist=persist,
            verify=verify,
            allow_dangerous=allow_dangerous,
        )
        return result[resolve_register_name(name)]

    async def set_settings(
        self,
        changes: Mapping[str, Any],
        *,
        persist: bool = True,
        verify: bool | None = None,
        allow_dangerous: bool = False,
        last_profile: str | None = None,
        replace_desired: bool = False,
        unset: Sequence[str] = (),
        raise_on_error: bool = True,
    ) -> dict[str, JSONValue | None]:
        """Validate, optionally persist, and apply multiple named settings."""
        if self._read_only:
            raise RegisterError("controller is in read-only mode")
        if self.config is None:
            await self.load_config()
        normalized = normalize_settings(changes, allow_dangerous=allow_dangerous)
        await validate_live_relations(self, normalized)
        current_desired = {} if replace_desired else self.desired
        active_profile = (
            last_profile
            if last_profile is not None
            else self.config.get("last_profile")
        )
        for item in unset:
            current_desired.pop(resolve_register_name(item), None)
        candidate = {**current_desired, **normalized}
        validate_cross_settings(candidate)
        if persist:
            for key in normalized:
                if not REGISTERS[key].restorable:
                    raise RegisterError(f"{key} must not be persisted/restored")
            updated = await self.config_store.update_desired(
                normalized,
                unset=unset,
                replace=replace_desired,
                last_profile=active_profile,
            )
            self.config["desired"] = updated
            self.config["last_profile"] = active_profile

        results: dict[str, JSONValue | None] = {}
        errors: dict[str, str] = {}
        order = self._write_order(normalized)
        for key in order:
            try:
                results[key] = await self._write_definition(
                    REGISTERS[key],
                    normalized[key],
                    verify=verify,
                    allow_dangerous=allow_dangerous,
                )
            except (WolfError, OSError) as exc:
                errors[key] = str(exc)
                if isinstance(exc, CommunicationError):
                    for remaining in order:
                        if remaining not in results and remaining not in errors:
                            errors[remaining] = "not attempted after communication failure"
                    break
        await self._write_state_file()
        if errors and raise_on_error:
            raise BulkWriteError(
                "one or more settings could not be applied; desired state "
                "remains saved for retry",
                results,
                errors,
            )
        return results

    async def set_ventilation_level(
        self, level: str | int, *, persist: bool = True
    ) -> dict[str, JSONValue | None]:
        """Select a preset ventilation level and level-based remote control."""
        return await self.set_settings(
            {"remote_ventilation_level": level, "remote_control_mode": "level"},
            persist=persist,
        )

    async def set_airflow(
        self, airflow_m3h: int, *, persist: bool = True
    ) -> dict[str, JSONValue | None]:
        """Select a direct airflow target and airflow-based remote control."""
        return await self.set_settings(
            {"remote_airflow_m3h": airflow_m3h, "remote_control_mode": "airflow"},
            persist=persist,
        )

    async def disable_remote_control(self, *, persist: bool = True) -> JSONValue | None:
        """Disable external remote control while optionally persisting ownership."""
        return await self.set_setting("remote_control_mode", "off", persist=persist)

    async def set_standby(
        self, enabled: bool, *, persist: bool = True
    ) -> JSONValue | None:
        """Enter or leave external standby mode."""
        return await self.set_setting("remote_standby", enabled, persist=persist)

    async def set_bypass_mode(
        self, mode: str | int, *, persist: bool = True
    ) -> JSONValue | None:
        """Select automatic, closed, or open bypass operation."""
        return await self.set_setting("bypass_mode", mode, persist=persist)

    async def set_flow_presets(
        self,
        *,
        holiday: int,
        low: int,
        normal: int,
        high: int,
        persist: bool = True,
    ) -> dict[str, JSONValue | None]:
        """Set the four ordered CWL-2-325 airflow presets together."""
        return await self.set_settings(
            {
                "flow_preset_holiday_m3h": holiday,
                "flow_preset_low_m3h": low,
                "flow_preset_normal_m3h": normal,
                "flow_preset_high_m3h": high,
            },
            persist=persist,
        )

    async def reset_filter_warning(self) -> str:
        """Send the filter reset action and return its read-back status if possible."""
        if self._read_only:
            raise RegisterError("controller is in read-only mode")
        register = REGISTERS["filter_reset_status"]
        await self._write_raw(register, 1, allow_dangerous=False)
        import asyncio

        await asyncio.sleep(0.2)
        try:
            await self._read_definition(register)
            return str(self._values[register.key].value)
        except CommunicationError:
            return "command_sent"

    async def reset_appliance(self, *, confirm: bool = False) -> str:
        """Send the guarded appliance reset and close the likely stale connection."""
        if not confirm:
            raise RegisterError("appliance reset requires confirm=True")
        if self._read_only:
            raise RegisterError("controller is in read-only mode")
        await self._write_raw(
            REGISTERS["appliance_reset_status"], 1, allow_dangerous=True
        )
        async with self._io_lock:
            self._close_client_locked()
        return "command_sent; the appliance may disconnect while rebooting"

    async def list_profiles(self) -> list[str]:
        """List configured profile names."""
        if self.config is None:
            await self.load_config()
        return await self.profile_loader.list_profiles()

    async def preview_profile(self, name: str) -> ResolvedProfile:
        """Resolve a profile without persisting or writing its settings."""
        if self.config is None:
            await self.load_config()
        return await self.profile_loader.load(name)

    async def apply_profile(
        self,
        name: str,
        *,
        persist: bool = True,
        replace: bool | None = None,
        raise_on_error: bool = True,
    ) -> dict[str, JSONValue | None]:
        """Resolve and apply a partial profile to desired state and the device."""
        profile = await self.preview_profile(name)
        return await self.set_settings(
            profile.settings,
            persist=persist,
            last_profile=profile.name if persist else None,
            replace_desired=profile.replace if replace is None else replace,
            unset=profile.unset,
            raise_on_error=raise_on_error,
        )

    async def apply_desired(
        self,
        *,
        force: bool = False,
        raise_on_error: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Reconcile persistent desired values, optionally rewriting every value."""
        if self._read_only:
            return {"written": {}, "skipped": {}, "errors": {}}
        if self.config is None:
            await self.load_config()
        desired = self.desired
        written: dict[str, Any] = {}
        skipped: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key in self._write_order(desired):
            register = REGISTERS[key]
            try:
                if not force:
                    state = self._values[key]
                    if not state.available:
                        await self._read_definition(register)
                    state = self._values[key]
                    if state.available and self._values_equal(register, state.value, desired[key]):
                        skipped[key] = state.value
                        continue
                written[key] = await self._write_definition(
                    register, desired[key], verify=None, allow_dangerous=False
                )
            except (WolfError, OSError) as exc:
                errors[key] = str(exc)
                if isinstance(exc, CommunicationError):
                    break
        if not errors:
            self._last_restored_generation = self._connection_generation
        await self._write_state_file()
        result = {"written": written, "skipped": skipped, "errors": errors}
        if errors and raise_on_error:
            raise BulkWriteError(
                "could not fully apply desired configuration", written, errors
            )
        return result

    @staticmethod
    def _write_order(settings: Mapping[str, Any]) -> list[str]:
        """Order target values before remote mode selection to avoid transients."""
        priority = {
            "remote_ventilation_level": 80,
            "remote_airflow_m3h": 80,
            "remote_standby": 90,
            "remote_control_mode": 100,
        }
        return sorted(
            settings,
            key=lambda key: (priority.get(key, 10), REGISTERS[key].address, key),
        )
