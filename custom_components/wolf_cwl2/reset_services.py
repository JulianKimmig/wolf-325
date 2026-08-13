"""Strongly guarded one-shot reset actions without a raw write escape hatch."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from wolf_325 import CommunicationError, RegisterError

from .const import CONF_ALLOW_APPLIANCE_RESET, DOMAIN
from .service_helpers import CONF_CONFIG_ENTRY_ID, runtime_for

RESET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required("confirmation"): cv.string,
    }
)


def async_register_reset_services(hass: HomeAssistant) -> None:
    """Register filter and appliance reset actions once.

    Args:
        hass: Home Assistant instance owning the service registry.

    Returns:
        None after synchronous service registration.
    """
    async def reset_filter(call: ServiceCall) -> dict[str, Any]:
        """Bind Home Assistant to one filter reset call.

        Args:
            call: Validated response-capable service call.

        Returns:
            Dispatch/readback status response.
        """
        return await _async_reset_filter(hass, call)

    async def reset_appliance(call: ServiceCall) -> dict[str, Any]:
        """Bind Home Assistant to one appliance reset call.

        Args:
            call: Validated response-capable service call.

        Returns:
            Dispatch-only status response.
        """
        return await _async_reset_appliance(hass, call)

    hass.services.async_register(
        DOMAIN,
        "reset_filter",
        reset_filter,
        schema=RESET_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "reset_appliance",
        reset_appliance,
        schema=RESET_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def _async_reset_filter(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, str]:
    """Validate and execute the dedicated filter reset path.

    Args:
        hass: Home Assistant instance owning config entries.
        call: Validated action call and exact confirmation phrase.

    Returns:
        Public client reset status.
    """
    runtime = runtime_for(hass, call)
    _require_control_mode(runtime.authority)
    if call.data["confirmation"] != "EXECUTE ACTION":
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="filter_confirmation",
        )
    async with runtime.operation_lock:
        _require_running(runtime.stopping)
        try:
            await _verify_live_identity(runtime)
            status = await runtime.controller.reset_filter_warning()
        except (CommunicationError, RegisterError) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reset_failed",
            ) from exc
        return {"status": status}


async def _async_reset_appliance(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, str]:
    """Validate every dangerous gate and dispatch one appliance reset.

    Args:
        hass: Home Assistant instance owning auth and config entries.
        call: Validated action call, context, and exact confirmation phrase.

    Returns:
        Dispatch-only status without claiming reboot completion.
    """
    runtime = runtime_for(hass, call)
    _require_control_mode(runtime.authority)
    options = runtime.coordinator.config_entry.options
    if not bool(options[CONF_ALLOW_APPLIANCE_RESET]):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="appliance_reset_disabled",
        )
    if call.data["confirmation"] != "RESET APPLIANCE":
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="appliance_confirmation",
        )
    user = (
        await hass.auth.async_get_user(call.context.user_id)
        if call.context.user_id is not None
        else None
    )
    if user is None or not user.is_admin:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="admin_required",
        )
    async with runtime.operation_lock:
        _require_running(runtime.stopping)
        try:
            await _verify_live_identity(runtime)
            await runtime.controller.reset_appliance(confirm=True)
        except (CommunicationError, RegisterError) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reset_failed",
            ) from exc
        runtime.coordinator.invalidate_after_appliance_reset()
        return {"status": "command_sent"}


async def _verify_live_identity(runtime: Any) -> None:
    """Refresh and compare serial identity immediately before a reset.

    Args:
        runtime: Loaded entry runtime held under its operation lock.

    Returns:
        None when the live serial matches the configured target.
    """
    await runtime.controller.refresh("serial_number")
    if runtime.controller.get_value("serial_number") != runtime.coordinator.expected_serial:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="identity_changed",
        )


def _require_control_mode(authority: str) -> None:
    """Reject reset actions in monitor-only mode.

    Args:
        authority: Canonical entry authority.

    Returns:
        None for temporary or persistent control.
    """
    if authority == "monitor_only":
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="control_required",
        )


def _require_running(stopping: bool) -> None:
    """Reject reset dispatch after unload begins.

    Args:
        stopping: Current runtime unload flag.

    Returns:
        None while the runtime remains active.
    """
    if stopping:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="entry_stopping",
        )
