"""Native numeric controls for safe WOLF CWL-2 settings."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from wolf_325 import REGISTERS

from .entity import WolfCWL2Entity
from .entity_catalogue import ENTITY_SPECS, EntitySpec
from .mutations import async_set_setting
from .runtime import WolfCWL2ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add every reviewed numeric setting for one entry.

    Args:
        hass: Home Assistant instance owning entity state.
        entry: Loaded entry with typed runtime data.
        async_add_entities: Platform callback used to register entities.

    Returns:
        None.
    """
    async_add_entities(
        WolfCWL2Number(entry, spec)
        for spec in ENTITY_SPECS.values()
        if spec.platform == "number"
    )


class WolfCWL2Number(WolfCWL2Entity, NumberEntity):
    """Control one safe numeric register through the shared mutation owner."""

    _attr_mode = NumberMode.BOX

    def __init__(self, entry: WolfCWL2ConfigEntry, spec: EntitySpec) -> None:
        """Initialize catalogue-derived numeric bounds and presentation.

        Args:
            entry: Serial-backed config entry with loaded runtime.
            spec: Reviewed numeric entity description.
        """
        super().__init__(entry.runtime_data.coordinator, entry, spec)
        register = REGISTERS[spec.key]
        assert register.minimum is not None
        assert register.maximum is not None
        candidates = (register.minimum, *register.extra_values)
        self._attr_native_min_value = min(candidates)
        self._attr_native_max_value = register.maximum
        self._attr_native_step = register.step or 1
        self._attr_native_unit_of_measurement = spec.native_unit

    @property
    def native_value(self) -> float | int | None:
        """Return the confirmed cached numeric value.

        Returns:
            Confirmed number, or ``None`` while unavailable.
        """
        value = self.coordinator.controller.get_value(self.spec.key)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    async def async_set_native_value(self, value: float) -> None:
        """Delegate a requested value to the serialized mutation owner.

        Args:
            value: Native number selected through Home Assistant.

        Returns:
            None after verified completion.
        """
        await async_set_setting(self.coordinator.config_entry.runtime_data, self.spec.key, value)
