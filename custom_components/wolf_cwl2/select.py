"""Native enum controls for safe WOLF CWL-2 settings."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from wolf_325 import REGISTERS

from .entity import WolfCWL2Entity
from .entity_catalogue import ENTITY_SPECS, EntitySpec
from .mutations import async_set_setting
from .const import DOMAIN
from .coordinator import WolfCWL2Coordinator
from .profile_operations import async_apply_profile
from .runtime import WolfCWL2ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WolfCWL2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add every reviewed enum setting for one entry.

    Args:
        hass: Home Assistant instance owning entity state.
        entry: Loaded entry with typed runtime data.
        async_add_entities: Platform callback used to register entities.

    Returns:
        None.
    """
    entities = [
        WolfCWL2Select(entry, spec)
        for spec in ENTITY_SPECS.values()
        if spec.platform == "select"
    ]
    entities.append(ProfileSelect(entry))
    async_add_entities(entities)


class WolfCWL2Select(WolfCWL2Entity, SelectEntity):
    """Control one known enum while retaining unknown confirmed states."""

    def __init__(self, entry: WolfCWL2ConfigEntry, spec: EntitySpec) -> None:
        """Initialize canonical enum options and common entity behavior.

        Args:
            entry: Serial-backed config entry with loaded runtime.
            spec: Reviewed select entity description.
        """
        super().__init__(entry.runtime_data.coordinator, entry, spec)
        choices = REGISTERS[spec.key].enum
        assert choices is not None
        self._attr_options = list(choices.values())

    @property
    def current_option(self) -> str | None:
        """Return the confirmed enum label, including unknown firmware values.

        Returns:
            Confirmed label or ``None`` while unavailable.
        """
        value = self.coordinator.controller.get_value(self.spec.key)
        return value if isinstance(value, str) else None

    async def async_select_option(self, option: str) -> None:
        """Delegate a known option to the serialized mutation owner.

        Args:
            option: Canonical enum label selected by the caller.

        Returns:
            None after verified completion.
        """
        await async_set_setting(self.coordinator.config_entry.runtime_data, self.spec.key, option)


class ProfileSelect(CoordinatorEntity[WolfCWL2Coordinator], SelectEntity):
    """Apply HA-owned profiles and report only the last full success."""

    _attr_has_entity_name = True
    _attr_translation_key = "profile"

    def __init__(self, entry: WolfCWL2ConfigEntry) -> None:
        """Initialize stable synthetic identity and current catalogue options.

        Args:
            entry: Serial-backed loaded config entry.
        """
        super().__init__(entry.runtime_data.coordinator)
        serial = entry.unique_id
        assert serial is not None
        self._runtime = entry.runtime_data
        self._attr_unique_id = f"{serial}_profile"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="WOLF",
            model="CWL-2-325",
            name=entry.title,
            serial_number=serial,
        )

    @property
    def options(self) -> list[str]:
        """Return current Store-owned profile names.

        Returns:
            Sorted profile identifiers refreshed after successful capture.
        """
        return list(self._runtime.profile_names)

    @property
    def current_option(self) -> str | None:
        """Return the last fully successful HA application.

        Returns:
            Profile name or ``None`` without a successful runtime application.
        """
        return self._runtime.last_applied_profile

    async def async_select_option(self, option: str) -> None:
        """Apply one selected Store-owned profile.

        Args:
            option: Existing profile identifier.

        Returns:
            None after complete verified application.
        """
        await async_apply_profile(self._runtime, option)
