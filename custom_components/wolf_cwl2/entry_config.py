"""Translate Home Assistant entry data into host-neutral client configuration."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from wolf_325 import DEFAULT_CONFIG

from .const import (
    CONF_AUTHORITY,
    CONF_FAST_INTERVAL,
    CONF_READ_EXTENSION,
    CONF_READ_HOLDING,
    CONF_RECONCILE_INTERVAL,
    CONF_SLOW_INTERVAL,
    CONF_STATIC_INTERVAL,
    DEFAULT_OPTIONS,
)
from .storage import EntryStore


def build_client_config(
    connection: Mapping[str, Any],
    options: Mapping[str, Any],
    store: EntryStore,
) -> dict[str, Any]:
    """Build a complete client config owned by one Home Assistant entry.

    Args:
        connection: Validated mutable endpoint facts from config-entry data.
        options: Validated authority and polling policy.
        store: Loaded per-entry persistence owner.

    Returns:
        Complete host-neutral public client configuration.
    """
    policy = {**DEFAULT_OPTIONS, **dict(options)}
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["connection"].update(copy.deepcopy(dict(connection)))
    config["polling"].update(
        {
            CONF_FAST_INTERVAL: policy[CONF_FAST_INTERVAL],
            CONF_SLOW_INTERVAL: policy[CONF_SLOW_INTERVAL],
            CONF_STATIC_INTERVAL: policy[CONF_STATIC_INTERVAL],
            CONF_RECONCILE_INTERVAL: policy[CONF_RECONCILE_INTERVAL],
            CONF_READ_HOLDING: policy[CONF_READ_HOLDING],
            CONF_READ_EXTENSION: policy[CONF_READ_EXTENSION],
        }
    )
    persistent = policy[CONF_AUTHORITY] == "persistent"
    config["persistence"].update(
        {
            "restore_on_startup": persistent,
            "restore_on_reconnect": persistent,
            "enforce_desired_state": persistent,
        }
    )
    config["desired"] = store.desired
    config["last_profile"] = store.last_profile
    config["profiles_dir"] = None
    config["state_file"] = None
    return config
