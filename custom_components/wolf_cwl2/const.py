"""Stable constants for the WOLF CWL-2 Home Assistant integration."""

from typing import Final

DOMAIN = "wolf_cwl2"
INTEGRATION_NAME = "WOLF CWL-2"

CONF_DEVICE_ID: Final = "device_id"
CONF_TRANSPORT: Final = "transport"
CONF_ADDRESS_OFFSET: Final = "address_offset"
CONF_AUTHORITY: Final = "authority"
CONF_FAST_INTERVAL: Final = "fast_interval_seconds"
CONF_SLOW_INTERVAL: Final = "slow_interval_seconds"
CONF_STATIC_INTERVAL: Final = "static_interval_seconds"
CONF_RECONCILE_INTERVAL: Final = "reconcile_interval_seconds"
CONF_READ_HOLDING: Final = "read_holding_registers"
CONF_READ_EXTENSION: Final = "read_extension_registers"
CONF_ALLOW_APPLIANCE_RESET: Final = "allow_appliance_reset"

AUTHORITY_MODES: Final = ("monitor_only", "temporary", "persistent")
MIN_INTERVAL_SECONDS: Final = 5
DEFAULT_OPTIONS: Final[dict[str, object]] = {
    CONF_AUTHORITY: "monitor_only",
    CONF_FAST_INTERVAL: 5,
    CONF_SLOW_INTERVAL: 60,
    CONF_STATIC_INTERVAL: 300,
    CONF_RECONCILE_INTERVAL: 30,
    CONF_READ_HOLDING: True,
    CONF_READ_EXTENSION: True,
    CONF_ALLOW_APPLIANCE_RESET: False,
}
