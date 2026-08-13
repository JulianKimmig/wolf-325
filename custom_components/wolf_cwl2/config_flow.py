"""Configuration, reconfigure, and options flows for WOLF CWL-2."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback

from .config_schema import connection_schema, intervals_are_valid, options_schema
from .const import DEFAULT_OPTIONS, DOMAIN, INTEGRATION_NAME
from .probe import CannotConnect, InvalidIdentity, async_probe_device


class WolfCWL2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create serial-backed entries through live read-only identity probes."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure one appliance from an operator-supplied endpoint.

        Args:
            user_input: Validated connection form values, or ``None`` initially.

        Returns:
            Form, actionable error, duplicate abort, or created config entry.
        """
        return await self._async_connection_step("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change an endpoint only after proving the same appliance serial.

        Args:
            user_input: Replacement connection values, or ``None`` initially.

        Returns:
            Form, actionable error, mismatch abort, or reload-triggering update.
        """
        return await self._async_connection_step("reconfigure", user_input)

    async def _async_connection_step(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Run the shared form and identity logic for user and reconfigure flows.

        Args:
            step_id: Home Assistant step identifier.
            user_input: Schema-normalized connection values or ``None``.

        Returns:
            Appropriate Home Assistant config-flow result.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            normalized_input = _normalize_connection(user_input)
            if normalized_input is None:
                errors[CONF_HOST] = "invalid_host"
            else:
                user_input = normalized_input
                try:
                    identity = await async_probe_device(user_input)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidIdentity:
                    errors["base"] = "invalid_identity"
                else:
                    await self.async_set_unique_id(identity.serial_number)
                    title = f"{INTEGRATION_NAME} {identity.serial_number}"
                    if step_id == "user":
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=title,
                            data=user_input,
                            options=dict(DEFAULT_OPTIONS),
                        )
                    entry = self._get_reconfigure_entry()
                    self._abort_if_unique_id_mismatch(reason="reconfigure_mismatch")
                    return self.async_update_reload_and_abort(
                        entry,
                        title=title,
                        data=user_input,
                    )
        defaults = (
            self._get_reconfigure_entry().data
            if step_id == "reconfigure"
            else user_input
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=connection_schema(defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the automatic-reload runtime policy flow.

        Args:
            config_entry: Entry whose options Home Assistant will update.

        Returns:
            New options flow; entry access is provided later by Home Assistant.
        """
        return WolfCWL2OptionsFlow()


class WolfCWL2OptionsFlow(OptionsFlowWithReload):
    """Edit authority, tier inclusion, and safe polling cadence."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and persist runtime policy with one automatic reload.

        Args:
            user_input: Schema-normalized options, or ``None`` initially.

        Returns:
            Options form, interval error, or completed options update.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            if intervals_are_valid(user_input):
                return self.async_create_entry(data=user_input)
            errors["base"] = "invalid_interval"
        defaults = user_input if user_input is not None else self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=options_schema(defaults),
            errors=errors,
        )


def _normalize_connection(user_input: dict[str, Any]) -> dict[str, Any] | None:
    """Strip the endpoint host after frontend-safe schema validation.

    Args:
        user_input: Schema-normalized connection form values.

    Returns:
        A copied mapping with a stripped host, or ``None`` for a blank host.
    """
    host = str(user_input[CONF_HOST]).strip()
    if not host:
        return None
    return {**user_input, CONF_HOST: host}
