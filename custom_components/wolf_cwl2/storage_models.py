"""Validation and construction for versioned integration Store payloads."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Final

from wolf_325 import example_profile_documents, normalize_settings

from .const import AUTHORITY_MODES

STORE_SCHEMA_VERSION: Final = 2


class StorePayloadError(ValueError):
    """Report a corrupt or unsupported integration-owned Store payload."""


class UnsupportedStoreSchemaError(StorePayloadError):
    """Report a Store wrapper or payload version newer than this integration."""


def new_store_payload() -> dict[str, Any]:
    """Create a new payload seeded with isolated canonical examples.

    Returns:
        JSON-safe current Store payload at revision zero.
    """
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "revision": 0,
        "desired": {},
        "last_profile": None,
        "last_applied_profile": None,
        "desired_active": False,
        "last_authority": None,
        "profiles": example_profile_documents(),
        "examples_seeded": True,
    }


def validate_store_payload(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and isolate one loaded Store payload.

    Args:
        raw: Deserialized integration-owned Store data.

    Returns:
        Canonical isolated payload.

    Raises:
        StorePayloadError: If the schema or any structural field is invalid.
    """
    schema_version = raw.get("schema_version")
    if schema_version != STORE_SCHEMA_VERSION:
        raise UnsupportedStoreSchemaError(
            f"unsupported store schema {schema_version!r}; "
            f"expected {STORE_SCHEMA_VERSION}"
        )
    revision = raw.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise StorePayloadError("store revision must be a non-negative integer")
    desired_raw = raw.get("desired")
    if not isinstance(desired_raw, Mapping):
        raise StorePayloadError("store desired must be an object")
    try:
        desired = normalize_settings(desired_raw, require_restorable=True)
    except Exception as exc:
        raise StorePayloadError(f"invalid stored desired state: {exc}") from exc
    profiles_raw = raw.get("profiles")
    if not isinstance(profiles_raw, Mapping) or not all(
        isinstance(name, str) and isinstance(document, Mapping)
        for name, document in profiles_raw.items()
    ):
        raise StorePayloadError("store profiles must map names to documents")
    last_profile = _optional_name(raw.get("last_profile"), "last_profile")
    last_applied = _optional_name(
        raw.get("last_applied_profile"), "last_applied_profile"
    )
    examples_seeded = raw.get("examples_seeded")
    if not isinstance(examples_seeded, bool):
        raise StorePayloadError("store examples_seeded must be a boolean")
    desired_active = raw.get("desired_active")
    if not isinstance(desired_active, bool):
        raise StorePayloadError("store desired_active must be a boolean")
    last_authority = raw.get("last_authority")
    if last_authority is not None and last_authority not in AUTHORITY_MODES:
        raise StorePayloadError("store last_authority must be a valid mode or null")
    return {
        "schema_version": STORE_SCHEMA_VERSION,
        "revision": revision,
        "desired": desired,
        "last_profile": last_profile,
        "last_applied_profile": last_applied,
        "desired_active": desired_active,
        "last_authority": last_authority,
        "profiles": copy.deepcopy(dict(profiles_raw)),
        "examples_seeded": examples_seeded,
    }


def migrate_store_payload(
    old_major_version: int,
    old_minor_version: int,
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    """Migrate one actual legacy Store wrapper and payload to current schema.

    Args:
        old_major_version: Home Assistant Store wrapper major version.
        old_minor_version: Home Assistant Store wrapper minor version.
        raw: Legacy integration-owned payload.

    Returns:
        Validated current payload with one migration revision increment.

    Raises:
        UnsupportedStoreSchemaError: If the wrapper or payload is not v1.
        StorePayloadError: If legacy content is structurally invalid.
    """
    if old_major_version != 1 or old_minor_version != 1:
        raise UnsupportedStoreSchemaError(
            "unsupported Store wrapper schema "
            f"{old_major_version}.{old_minor_version}"
        )
    if raw.get("schema_version") != 1:
        raise UnsupportedStoreSchemaError(
            f"unsupported store schema {raw.get('schema_version')!r}; expected 1"
        )
    revision = raw.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise StorePayloadError("store revision must be a non-negative integer")
    migrated = copy.deepcopy(dict(raw))
    migrated["schema_version"] = STORE_SCHEMA_VERSION
    migrated["revision"] = revision + 1
    migrated.setdefault("desired_active", False)
    migrated.setdefault("last_authority", None)
    return validate_store_payload(migrated)


def _optional_name(value: Any, field: str) -> str | None:
    """Validate an optional stored profile identifier.

    Args:
        value: Deserialized field value.
        field: Field name used in validation errors.

    Returns:
        String identifier or ``None``.

    Raises:
        StorePayloadError: If the value is neither a non-empty string nor null.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise StorePayloadError(f"store {field} must be a non-empty string or null")
    return value
