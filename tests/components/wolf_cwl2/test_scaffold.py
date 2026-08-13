"""Tests for the native WOLF CWL-2 custom-component scaffold."""

from __future__ import annotations

import json
from pathlib import Path
import struct
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wolf_cwl2.const import DOMAIN

from .fakes import FakeGateway
from .test_config_flow import CONNECTION, DEFAULT_OPTIONS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

COMPONENT_ROOT = Path(__file__).parents[3] / "custom_components" / DOMAIN
REPOSITORY_ROOT = COMPONENT_ROOT.parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    """Read one component JSON document for structural assertions.

    Args:
        path: JSON document path.

    Returns:
        Parsed top-level mapping.
    """
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_manifest_and_custom_translation_are_complete() -> None:
    """Verify the loadable local manifest and custom translation structure.

    Returns:
        None.
    """
    manifest = _read_json(COMPONENT_ROOT / "manifest.json")
    assert manifest == {
        "codeowners": ["@JulianKimmig"],
        "config_flow": True,
        "documentation": "https://github.com/JulianKimmig/wolf-325#readme",
        "domain": DOMAIN,
        "integration_type": "device",
        "iot_class": "local_polling",
        "issue_tracker": "https://github.com/JulianKimmig/wolf-325/issues",
        "name": "WOLF CWL-2",
        "requirements": ["wolf-325==0.1.0"],
        "version": "0.1.0",
    }

    translations = _read_json(COMPONENT_ROOT / "translations" / "en.json")
    assert translations["title"] == "WOLF CWL-2"
    assert "config" in translations
    assert not (COMPONENT_ROOT / "strings.json").exists()


def test_local_hacs_layout_and_brand_asset_are_structurally_complete() -> None:
    """Validate safe local HACS metadata without inventing release ownership.

    Returns:
        None.
    """
    assert _read_json(REPOSITORY_ROOT / "hacs.json") == {"name": "WOLF CWL-2"}
    assert (REPOSITORY_ROOT / ".github" / "CODEOWNERS").read_text(
        encoding="utf-8"
    ) == "* @JulianKimmig\n"
    integration_directories = sorted(
        path.name
        for path in (REPOSITORY_ROOT / "custom_components").iterdir()
        if path.is_dir() and (path / "manifest.json").is_file()
    )
    assert integration_directories == [DOMAIN]

    icon = (COMPONENT_ROOT / "brand" / "icon.png").read_bytes()
    assert icon.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", icon[16:24])
    assert width == height
    assert width >= 256


async def test_entry_loads_and_unloads_with_runtime_poll(
    hass: HomeAssistant,
    fake_gateway: FakeGateway,
) -> None:
    """Verify the scaffold owns the real runtime lifecycle.

    Args:
        hass: Home Assistant test instance.
        fake_gateway: External Modbus boundary fake.

    Returns:
        None.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test CWL-2",
        unique_id="123456789012",
        data=CONNECTION,
        options=DEFAULT_OPTIONS,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert fake_gateway.reads
    assert entry.runtime_data.controller._tasks == []

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert all(not client.connected for client in fake_gateway.clients)
