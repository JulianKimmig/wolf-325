"""Actionable repair creation, dismissal, resolution, and exclusion tests."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN
from custom_components.wolf_cwl2.repairs import issue_id_for
from custom_components.wolf_cwl2.storage_models import (
    STORE_SCHEMA_VERSION,
    new_store_payload,
)

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(serial: str, *, entry_id: str | None = None) -> MockConfigEntry:
    """Build one detached entry for setup-fault repair tests.

    Args:
        serial: Expected live appliance identity.
        entry_id: Optional stable Home Assistant entry identifier.

    Returns:
        Detached config entry.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        title="Repair test ventilation",
        unique_id=serial,
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )


async def test_identity_repair_is_persistent_dismissible_and_resolves(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Create one identity repair and remove it after verified recovery.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = _entry("999999999999", entry_id="private-identity-entry")
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    registry = ir.async_get(hass)
    issue_id = issue_id_for("identity_mismatch", entry.entry_id)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.is_persistent
    assert not issue.is_fixable
    assert entry.entry_id not in issue_id

    registry.async_ignore(DOMAIN, issue_id, True)
    assert registry.async_get_issue(DOMAIN, issue_id).dismissed_version is not None
    fake_gateway.serial = "999999999999"
    fake_gateway.apply_identity()
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert registry.async_get_issue(DOMAIN, issue_id) is None


@pytest.mark.parametrize(
    ("fault", "payload"),
    [
        ("unsupported_store", {"schema_version": 99, "revision": 7}),
        (
            "corrupt_store",
            {
                **new_store_payload(),
                "profiles": {
                    "first": {"extends": "second", "settings": {}},
                    "second": {"extends": "first", "settings": {}},
                },
            },
        ),
    ],
)
async def test_store_fault_repairs_precede_io_and_resolve_after_restore(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
    fault: str,
    payload: dict[str, object],
) -> None:
    """Classify invalid Store data without touching the appliance.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.
        fault: Expected stable repair category.
        payload: Invalid integration payload stored before setup.

    Returns:
        None.
    """
    entry = _entry("123456789012")
    entry.add_to_hass(hass)
    raw: Store[dict[str, object]] = Store(
        hass,
        version=STORE_SCHEMA_VERSION,
        key=f"{DOMAIN}.{entry.entry_id}",
        private=True,
        atomic_writes=True,
    )
    await raw.async_save(payload)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert fake_gateway.reads == []
    assert fake_gateway.writes == []
    registry = ir.async_get(hass)
    issue_id = issue_id_for(fault, entry.entry_id)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == fault

    await raw.async_save(new_store_payload())
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_transient_connection_failure_creates_no_repair(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Keep ordinary reachability failure in retry state without an issue.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    fake_gateway.connects = False
    entry = _entry("123456789012")
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert not any(domain == DOMAIN for domain, _ in ir.async_get(hass).issues)
