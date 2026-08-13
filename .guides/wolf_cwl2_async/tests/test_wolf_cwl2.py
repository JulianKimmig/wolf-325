from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from wolf_cwl2 import DEFAULT_CONFIG, REGISTERS, WolfCWL2, _atomic_json_write_sync


class FakeResponse:
    def __init__(self, registers: list[int] | None = None) -> None:
        self.registers = registers or []

    def isError(self) -> bool:
        return False


class FakeClient:
    def __init__(self) -> None:
        self.connected = True
        self.input: dict[int, int] = {}
        self.holding: dict[int, int] = {}
        self.writes: list[tuple[int, int, int]] = []

    async def read_input_registers(
        self, address: int, *, count: int = 1, device_id: int = 1, **_: Any
    ) -> FakeResponse:
        return FakeResponse(
            [self.input.get(address + offset, 0) for offset in range(count)]
        )

    async def read_holding_registers(
        self, address: int, *, count: int = 1, device_id: int = 1, **_: Any
    ) -> FakeResponse:
        return FakeResponse(
            [self.holding.get(address + offset, 0) for offset in range(count)]
        )

    async def write_register(
        self, address: int, value: int, *, device_id: int = 1, **_: Any
    ) -> FakeResponse:
        self.writes.append((address, value, device_id))
        # Register 8003 has asymmetric write-command/read-state semantics.
        if address == 8003:
            self.holding[address] = 1 if value == 1 else 0
        else:
            self.holding[address] = value
        return FakeResponse([])

    def close(self) -> None:
        self.connected = False


class CodecTests(unittest.TestCase):
    def test_temperature_signed_scaling(self) -> None:
        register = REGISTERS["supply_temperature_c"]
        self.assertEqual(register.decode([0xFF85]), -12.3)

    def test_version_and_serial(self) -> None:
        version = REGISTERS["base_software_version"]
        self.assertEqual(
            version.decode([(ord("S") << 8) | 1, (2 << 8) | 3, 45]), "S1.02.03.0045"
        )
        serial = REGISTERS["serial_number"]
        self.assertEqual(serial.decode([0x1234, 0x5678, 0x9012]), "123456789012")

    def test_cwl325_airflow_validation(self) -> None:
        holiday = REGISTERS["flow_preset_holiday_m3h"]
        register = REGISTERS["flow_preset_low_m3h"]
        self.assertEqual(holiday.normalize(0), 0)
        self.assertEqual(register.normalize(150), 150)
        with self.assertRaises(Exception):
            register.normalize(0)
        with self.assertRaises(Exception):
            register.normalize(49)
        with self.assertRaises(Exception):
            register.normalize(151)


class ControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config_path = self.root / "config.json"
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["connection"]["host"] = "fake-gateway"
        config["state_file"] = "state.json"
        _atomic_json_write_sync(self.config_path, config)
        profiles = self.root / "profiles"
        profiles.mkdir()
        _atomic_json_write_sync(
            profiles / "night.json",
            {
                "description": "test profile",
                "settings": {
                    "remote_ventilation_level": "low",
                    "remote_control_mode": "level",
                    "remote_standby": False,
                },
            },
        )
        self.controller = WolfCWL2(self.config_path)
        await self.controller.load_config()
        self.fake = FakeClient()
        self.controller._client = self.fake  # Test injection; avoids a real network.

    async def asyncTearDown(self) -> None:
        await self.controller.stop()
        self.temp.cleanup()

    async def test_function_updates_device_and_config(self) -> None:
        await self.controller.set_ventilation_level("high")
        self.assertEqual(self.fake.holding[8001], 3)
        self.assertEqual(self.fake.holding[8000], 1)
        saved = json.loads(self.config_path.read_text())
        self.assertEqual(saved["desired"]["remote_ventilation_level"], "high")
        self.assertEqual(saved["desired"]["remote_control_mode"], "level")

    async def test_profile_is_partial_and_persistent(self) -> None:
        await self.controller.set_setting("bypass_mode", "automatic")
        await self.controller.apply_profile("night")
        saved = json.loads(self.config_path.read_text())
        self.assertEqual(saved["desired"]["bypass_mode"], "automatic")
        self.assertEqual(saved["desired"]["remote_ventilation_level"], "low")
        self.assertFalse(saved["desired"]["remote_standby"])
        self.assertEqual(saved["last_profile"], "night")

    async def test_startup_force_rewrites_desired_values(self) -> None:
        await self.controller.set_ventilation_level("normal")
        self.fake.writes.clear()
        self.fake.holding[8000] = 0
        self.fake.holding[8001] = 0
        await self.controller.start(restore=True, background=False)
        written_addresses = [address for address, _, _ in self.fake.writes]
        self.assertIn(8001, written_addresses)
        self.assertIn(8000, written_addresses)
        # Mode is intentionally written after its target value.
        self.assertLess(written_addresses.index(8001), written_addresses.index(8000))


if __name__ == "__main__":
    unittest.main()
