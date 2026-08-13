"""Single-owner Home Assistant mutation boundary for safe settings."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from wolf_325 import (
    BulkWriteError,
    CommunicationError,
    RegisterError,
    VerificationError,
)

from .coordinator import CoordinatorData
from .const import DOMAIN
from .runtime import EntryRuntime


async def async_set_setting(
    runtime: EntryRuntime,
    key: str,
    value: Any,
) -> None:
    """Validate authority, serialize, write, and publish confirmed state.

    Args:
        runtime: Per-entry resource and authority owner.
        key: Canonical safe setting key.
        value: Native Home Assistant value selected by the caller.

    Returns:
        None after verified client completion and coordinator publication.

    Raises:
        ServiceValidationError: If policy or caller input rejects the request.
        HomeAssistantError: If runtime communication or verification fails.
    """
    async with runtime.operation_lock:
        if runtime.stopping:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="entry_stopping",
            )
        if runtime.authority == "monitor_only":
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="monitor_only",
            )
        if not runtime.coordinator.last_update_success:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="appliance_unavailable",
            )
        if not runtime.controller.connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="appliance_disconnected",
            )
        serial = runtime.controller.get_value("serial_number")
        if serial != runtime.coordinator.expected_serial:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="identity_changed",
            )
        if runtime.authority == "persistent" and not runtime.store.desired_active:
            if runtime.store.desired:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="desired_dormant",
                )
            await runtime.store.async_set_desired_active(True)
        try:
            await runtime.controller.set_setting(
                key,
                value,
                persist=runtime.authority == "persistent",
            )
        except (CommunicationError, VerificationError, BulkWriteError) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="setting_not_confirmed",
            ) from exc
        except RegisterError as exc:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_setting",
                translation_placeholders={"detail": str(exc)},
            ) from exc
        publish_confirmed_state(runtime)


def publish_confirmed_state(runtime: EntryRuntime) -> None:
    """Notify entity listeners with a fresh immutable cache snapshot.

    Args:
        runtime: Entry whose controller cache completed a verified write.

    Returns:
        None after coordinator listeners are scheduled.
    """
    previous = runtime.coordinator.data
    assert previous is not None
    runtime.coordinator.async_set_updated_data(
        CoordinatorData(
            snapshot=runtime.controller.snapshot(),
            refreshed_tiers=(),
            tier_last_success=previous.tier_last_success,
            reconcile_errors=previous.reconcile_errors,
            desired_pending=previous.desired_pending,
        )
    )
