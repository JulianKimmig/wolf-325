"""Shared cache-only Home Assistant entity behavior for one appliance."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from wolf_325 import REGISTERS

from .const import DOMAIN
from .coordinator import WolfCWL2Coordinator
from .entity_catalogue import EntitySpec
from .runtime import WolfCWL2ConfigEntry


class WolfCWL2Entity(CoordinatorEntity[WolfCWL2Coordinator]):
    """Provide stable identity, grouping, defaults, and truthful availability."""

    _attr_force_update = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WolfCWL2Coordinator,
        entry: WolfCWL2ConfigEntry,
        spec: EntitySpec,
    ) -> None:
        """Initialize a register-backed entity without performing device I/O.

        Args:
            coordinator: Sole polling and confirmed-state owner for the entry.
            entry: Serial-backed Home Assistant config entry.
            spec: Reviewed Home Assistant presentation metadata.
        """
        super().__init__(coordinator)
        serial = entry.unique_id
        assert serial is not None
        self.spec = spec
        self._attr_unique_id = f"{serial}_{spec.key}"
        self._attr_translation_key = "register"
        self._attr_translation_placeholders = {"name": spec.name}
        self._attr_entity_registry_enabled_default = spec.enabled_default
        if spec.entity_category is not None:
            self._attr_entity_category = EntityCategory(spec.entity_category)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="WOLF",
            model="CWL-2-325",
            name=entry.title,
            serial_number=serial,
        )

    @property
    def available(self) -> bool:
        """Combine update, connection, tier freshness, and value availability.

        Returns:
            ``True`` only while the confirmed cached value is usable.
        """
        register = REGISTERS[self.spec.key]
        state = self.coordinator.controller.get_state(self.spec.key)
        return (
            super().available
            and self.coordinator.controller.connected
            and register.poll != "never"
            and self.coordinator.tier_is_fresh(register.poll)
            and bool(state["available"])
        )
