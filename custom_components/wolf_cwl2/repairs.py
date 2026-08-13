"""Persistent actionable issue ownership without sensitive identifiers."""

from __future__ import annotations

import hashlib
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

ISSUE_TYPES: Final = (
    "identity_mismatch",
    "corrupt_store",
    "unsupported_store",
)


def issue_id_for(kind: str, entry_id: str) -> str:
    """Return one stable opaque issue identifier for an entry fault.

    Args:
        kind: Approved actionable repair category.
        entry_id: Sensitive config-entry identifier to hash.

    Returns:
        Category plus a one-way stable entry discriminator.

    Raises:
        ValueError: If ``kind`` is not an approved repair category.
    """
    if kind not in ISSUE_TYPES:
        raise ValueError(f"unsupported repair category {kind!r}")
    digest = hashlib.sha256(entry_id.encode("utf-8")).hexdigest()[:16]
    return f"{kind}_{digest}"


def create_entry_issue(hass: HomeAssistant, kind: str, entry_id: str) -> None:
    """Create or reactivate one persistent non-destructive repair issue.

    Args:
        hass: Home Assistant instance owning the issue registry.
        kind: Approved actionable repair category.
        entry_id: Sensitive config-entry identifier used only for hashing.

    Returns:
        None after synchronous issue-registry mutation.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id_for(kind, entry_id),
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=kind,
    )


def clear_entry_issue(hass: HomeAssistant, kind: str, entry_id: str) -> None:
    """Delete one resolved entry issue if it exists.

    Args:
        hass: Home Assistant instance owning the issue registry.
        kind: Approved actionable repair category.
        entry_id: Sensitive config-entry identifier used only for hashing.

    Returns:
        None after synchronous issue-registry mutation.
    """
    ir.async_delete_issue(hass, DOMAIN, issue_id_for(kind, entry_id))
