"""End-user schemas and validation for connection and runtime policy flows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import (
    AUTHORITY_MODES,
    CONF_ADDRESS_OFFSET,
    CONF_ALLOW_APPLIANCE_RESET,
    CONF_AUTHORITY,
    CONF_DEVICE_ID,
    CONF_FAST_INTERVAL,
    CONF_READ_EXTENSION,
    CONF_READ_HOLDING,
    CONF_RECONCILE_INTERVAL,
    CONF_SLOW_INTERVAL,
    CONF_STATIC_INTERVAL,
    CONF_TRANSPORT,
    DEFAULT_OPTIONS,
    MIN_INTERVAL_SECONDS,
)

INTERVAL_FIELDS = (
    CONF_FAST_INTERVAL,
    CONF_SLOW_INTERVAL,
    CONF_STATIC_INTERVAL,
    CONF_RECONCILE_INTERVAL,
)


def connection_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build a connection form with optional current-value defaults.

    Args:
        defaults: Existing connection values for reconfiguration.

    Returns:
        Voluptuous schema accepted by Home Assistant config flows.
    """
    values = dict(defaults or {})
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=values.get(CONF_HOST, "")): _host,
            vol.Required(CONF_PORT, default=values.get(CONF_PORT, 502)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_DEVICE_ID, default=values.get(CONF_DEVICE_ID, 20)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
            vol.Required(
                CONF_TRANSPORT, default=values.get(CONF_TRANSPORT, "modbus_tcp")
            ): vol.In(("modbus_tcp", "rtu_over_tcp")),
            vol.Required(
                CONF_ADDRESS_OFFSET, default=values.get(CONF_ADDRESS_OFFSET, 0)
            ): vol.In((-1, 0)),
        }
    )


def options_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build the authority, cadence, and tier options form.

    Args:
        defaults: Existing entry options overlaid on canonical defaults.

    Returns:
        Voluptuous schema accepted by the Home Assistant options flow.
    """
    values = {**DEFAULT_OPTIONS, **dict(defaults or {})}
    return vol.Schema(
        {
            vol.Required(CONF_AUTHORITY, default=values[CONF_AUTHORITY]): vol.In(
                AUTHORITY_MODES
            ),
            **{
                vol.Required(field, default=values[field]): vol.Coerce(int)
                for field in INTERVAL_FIELDS
            },
            vol.Required(
                CONF_READ_HOLDING, default=values[CONF_READ_HOLDING]
            ): bool,
            vol.Required(
                CONF_READ_EXTENSION, default=values[CONF_READ_EXTENSION]
            ): bool,
            vol.Required(
                CONF_ALLOW_APPLIANCE_RESET,
                default=values[CONF_ALLOW_APPLIANCE_RESET],
            ): bool,
        }
    )


def intervals_are_valid(options: Mapping[str, Any]) -> bool:
    """Return whether every configured cadence meets the hard safety floor.

    Args:
        options: Schema-normalized options mapping.

    Returns:
        ``True`` only when every interval is at least five seconds.
    """
    return all(int(options[field]) >= MIN_INTERVAL_SECONDS for field in INTERVAL_FIELDS)


def _host(value: Any) -> str:
    """Normalize a non-empty endpoint host without inventing a fallback.

    Args:
        value: User-supplied host value.

    Returns:
        Stripped host string.

    Raises:
        vol.Invalid: If the value is empty after stripping.
    """
    host = str(value).strip()
    if not host:
        raise vol.Invalid("host must not be empty")
    return host
