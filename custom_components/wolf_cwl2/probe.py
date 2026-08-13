"""Read-only appliance identity probing through the public WOLF client."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from wolf_325 import CommunicationError, DEFAULT_CONFIG, WolfCWL2, WolfError


class CannotConnect(RuntimeError):
    """Report that the configured external gateway could not be queried."""


class InvalidIdentity(RuntimeError):
    """Report that live values cannot prove a supported appliance identity."""


@dataclass(frozen=True, slots=True)
class DeviceIdentity:
    """Contain stable values proven by one read-only setup probe.

    Attributes:
        serial_number: Verified 12-digit config-entry identity.
        appliance_type: Live internal appliance type for compatibility evidence.
    """

    serial_number: str
    appliance_type: int


async def async_probe_device(connection: Mapping[str, Any]) -> DeviceIdentity:
    """Read and validate appliance identity without restoration or background work.

    Args:
        connection: Validated client connection fields from a config flow.

    Returns:
        Verified serial-backed device identity.

    Raises:
        CannotConnect: If the gateway or appliance cannot be read.
        InvalidIdentity: If live identity values are malformed or unsupported.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["connection"].update(copy.deepcopy(dict(connection)))
    config["persistence"].update(
        {
            "restore_on_startup": False,
            "restore_on_reconnect": False,
            "enforce_desired_state": False,
        }
    )
    config["state_file"] = None
    config["profiles_dir"] = None
    controller = WolfCWL2.from_config(config)
    try:
        await controller.start(
            restore=False,
            background=False,
            read_only=True,
            initial_poll=False,
        )
        serial = await controller.refresh("serial_number")
        appliance_type = await controller.refresh("appliance_type")
    except CommunicationError as exc:
        raise CannotConnect("unable to query configured appliance") from exc
    except WolfError as exc:
        raise InvalidIdentity("unable to decode appliance identity") from exc
    finally:
        await controller.stop()
    if (
        not isinstance(serial, str)
        or len(serial) != 12
        or not serial.isdigit()
        or set(serial) == {"0"}
    ):
        raise InvalidIdentity("appliance serial is not a stable 12-digit identity")
    if not isinstance(appliance_type, int) or isinstance(appliance_type, bool):
        raise InvalidIdentity("appliance type is not a supported integer identity")
    return DeviceIdentity(serial, appliance_type)
