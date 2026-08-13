"""Baseline tests for the Home Assistant integration test environment."""

from homeassistant.core import HomeAssistant

from wolf_325 import WolfCWL2


def test_home_assistant_and_client_import_together() -> None:
    """Verify Home Assistant and the public client coexist in one environment.

    Returns:
        None.
    """
    assert HomeAssistant.__module__ == "homeassistant.core"
    assert WolfCWL2.__module__ == "wolf_325.controller"


def test_home_assistant_fixture_is_available(hass: HomeAssistant) -> None:
    """Verify the extracted Home Assistant pytest fixture is operational.

    Args:
        hass: Home Assistant test instance supplied by the external harness.

    Returns:
        None.
    """
    assert isinstance(hass, HomeAssistant)
