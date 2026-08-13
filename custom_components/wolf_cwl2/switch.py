"""Native Boolean controls for safe WOLF CWL-2 settings."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import WolfCWL2Entity
from .entity_catalogue import ENTITY_SPECS, EntitySpec
from .mutations import async_set_setting
from .runtime import WolfCWL2ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add every reviewed Boolean setting for one entry.

    Args:
        hass: Home Assistant instance owning entity state.
        entry: Loaded entry with typed runtime data.
        async_add_entities: Platform callback used to register entities.

    Returns:
        None.
    """
    async_add_entities(
        WolfCWL2Switch(entry, spec)
        for spec in ENTITY_SPECS.values()
        if spec.platform == "switch"
    )


class WolfCWL2Switch(WolfCWL2Entity, SwitchEntity):
    """Control one safe Boolean register through the shared mutation owner."""

    def __init__(self, entry: WolfCWL2ConfigEntry, spec: EntitySpec) -> None:
        """Initialize common switch identity and state behavior.

        Args:
            entry: Serial-backed config entry with loaded runtime.
            spec: Reviewed switch entity description.
        """
        super().__init__(entry.runtime_data.coordinator, entry, spec)

    @property
    def is_on(self) -> bool | None:
        """Return the confirmed Boolean setting state.

        Returns:
            Confirmed Boolean, or ``None`` while unavailable.
        """
        value = self.coordinator.controller.get_value(self.spec.key)
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Request and verify the enabled state.

        Args:
            **kwargs: Unused Home Assistant service context.

        Returns:
            None after verified completion.
        """
        await async_set_setting(self.coordinator.config_entry.runtime_data, self.spec.key, True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Request and verify the disabled state.

        Args:
            **kwargs: Unused Home Assistant service context.

        Returns:
            None after verified completion.
        """
        await async_set_setting(self.coordinator.config_entry.runtime_data, self.spec.key, False)
