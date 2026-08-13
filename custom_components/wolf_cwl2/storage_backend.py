"""Home Assistant Store wrapper with explicit integration data migrations."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .storage_models import STORE_SCHEMA_VERSION, migrate_store_payload


class MigratingEntryDataStore(Store[dict[str, Any]]):
    """Persist one entry payload while owning every supported schema migration."""

    def __init__(self, hass: HomeAssistant, key: str) -> None:
        """Initialize the current private and atomic Store wrapper.

        Args:
            hass: Home Assistant instance providing filesystem ownership.
            key: Private Store key for exactly one config entry.
        """
        super().__init__(
            hass,
            version=STORE_SCHEMA_VERSION,
            key=key,
            private=True,
            atomic_writes=True,
        )

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Migrate an actual legacy wrapper through the pure payload function.

        Args:
            old_major_version: Stored Home Assistant wrapper major version.
            old_minor_version: Stored Home Assistant wrapper minor version.
            old_data: Deserialized legacy integration payload.

        Returns:
            Validated current integration payload.
        """
        return migrate_store_payload(
            old_major_version,
            old_minor_version,
            old_data,
        )
