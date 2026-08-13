"""Explicit persistent-ownership workflow buttons for WOLF CWL-2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WolfCWL2Coordinator
from .mutations import publish_confirmed_state
from .runtime import EntryRuntime, WolfCWL2ConfigEntry

ButtonOperation = Callable[[EntryRuntime], Awaitable[None]]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add explicit resume and clear ownership buttons.

    Args:
        hass: Home Assistant instance owning entity state.
        entry: Loaded entry with typed runtime data.
        async_add_entities: Platform callback used to register entities.

    Returns:
        None.
    """
    async_add_entities(
        (
            DesiredButton(entry, "resume_desired", async_resume_desired),
            DesiredButton(entry, "clear_desired", async_clear_desired),
        )
    )


class DesiredButton(CoordinatorEntity[WolfCWL2Coordinator], ButtonEntity):
    """Run one explicit persistent desired-state transition."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: WolfCWL2ConfigEntry,
        key: str,
        operation: ButtonOperation,
    ) -> None:
        """Initialize stable synthetic identity and operation callback.

        Args:
            entry: Serial-backed loaded config entry.
            key: Stable synthetic action key and translation key.
            operation: Awaited whole-operation transition.
        """
        super().__init__(entry.runtime_data.coordinator)
        serial = entry.unique_id
        assert serial is not None
        self._runtime = entry.runtime_data
        self._operation = operation
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="WOLF",
            model="CWL-2-325",
            name=entry.title,
            serial_number=serial,
        )

    async def async_press(self) -> None:
        """Execute the selected transition through its entry runtime.

        Returns:
            None after durable transition completion.
        """
        await self._operation(self._runtime)


async def async_resume_desired(runtime: EntryRuntime) -> None:
    """Activate and immediately apply retained desired ownership.

    Args:
        runtime: Per-entry resource and authority owner.

    Returns:
        None after a fully successful forced apply.
    """
    async with runtime.operation_lock:
        _require_persistent(runtime)
        await runtime.controller.refresh("serial_number")
        if runtime.controller.get_value("serial_number") != runtime.coordinator.expected_serial:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="identity_changed"
            )
        await runtime.store.async_set_desired_active(True)
        result = await runtime.controller.apply_desired(
            force=True, raise_on_error=False
        )
        if result["errors"]:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="desired_apply_incomplete",
            )
        runtime.coordinator.defer_reconciliation()
        publish_confirmed_state(runtime)


async def async_clear_desired(runtime: EntryRuntime) -> None:
    """Release every owned desired key without writing a replacement value.

    Args:
        runtime: Per-entry resource and authority owner.

    Returns:
        None after durable ownership removal.
    """
    async with runtime.operation_lock:
        _require_persistent(runtime)
        await runtime.controller.set_settings(
            {},
            persist=True,
            unset=tuple(runtime.controller.desired),
        )
        await runtime.store.async_set_desired_active(False)
        publish_confirmed_state(runtime)


def _require_persistent(runtime: EntryRuntime) -> None:
    """Reject a desired-state transition outside active runtime policy.

    Args:
        runtime: Entry runtime being checked under its operation lock.

    Returns:
        None when persistent mutation is allowed.

    Raises:
        ServiceValidationError: If lifecycle or authority rejects the action.
    """
    if runtime.stopping or runtime.authority != "persistent":
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="persistent_required",
        )
