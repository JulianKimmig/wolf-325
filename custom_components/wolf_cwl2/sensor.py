"""Complete cache-only sensor platform for confirmed appliance values."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import WolfCWL2Coordinator
from .entity import WolfCWL2Entity
from .entity_catalogue import ENTITY_SPECS, EntitySpec
from .runtime import WolfCWL2ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add every reviewed sensor disposition for one config entry.

    Args:
        hass: Home Assistant instance owning entity state.
        entry: Loaded entry with typed runtime data.
        async_add_entities: Platform callback used to register entities.

    Returns:
        None.
    """
    async_add_entities(
        WolfCWL2Sensor(entry.runtime_data.coordinator, entry, spec)
        for spec in ENTITY_SPECS.values()
        if spec.platform == "sensor"
    )


class WolfCWL2Sensor(WolfCWL2Entity, SensorEntity):
    """Publish one confirmed canonical register through the sensor platform."""

    def __init__(
        self,
        coordinator: WolfCWL2Coordinator,
        entry: WolfCWL2ConfigEntry,
        spec: EntitySpec,
    ) -> None:
        """Initialize sensor presentation metadata and common identity.

        Args:
            coordinator: Sole polling coordinator for this appliance.
            entry: Serial-backed config entry.
            spec: Reviewed sensor presentation description.
        """
        super().__init__(coordinator, entry, spec)
        self._attr_native_unit_of_measurement = spec.native_unit
        self._attr_suggested_display_precision = spec.suggested_precision
        if spec.device_class is not None:
            self._attr_device_class = SensorDeviceClass(spec.device_class)
        if spec.state_class is not None:
            self._attr_state_class = SensorStateClass(spec.state_class)

    @property
    def native_value(self) -> bool | float | int | str | None:
        """Return one confirmed cached value without performing device I/O.

        Returns:
            Home Assistant-compatible native scalar, or ``None``.
        """
        value = self.coordinator.controller.get_value(self.spec.key)
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        return value
