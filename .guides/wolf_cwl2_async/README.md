# Async WOLF CWL-2-325 controller

`wolf_cwl2.py` is a Python 3.11+ async Modbus controller for a WOLF CWL-2-325 connected through a Waveshare RS485-to-Ethernet gateway. It can be imported as a library or run as a small daemon.

It provides:

- continuous polling of every documented UWA2-B/UWA2-E input register and every normal holding register;
- an in-memory value cache, callbacks, and an async update iterator;
- named, validated async setter functions instead of raw register writes;
- atomic JSON persistence of desired settings;
- forced restoration of desired settings at startup and after a reconnect;
- periodic desired-state reconciliation;
- separate partial JSON profiles, including profile inheritance;
- one-shot filter reset and guarded appliance reset;
- a JSON state file that other local software can consume;
- a CLI for testing, reading, setting, profiles, and long-running operation.

The register catalogue contains 154 logical values. See [`REGISTER_MAP.md`](REGISTER_MAP.md).

## Important limitation

The code was validated against the published register map and tested with a simulated Modbus client. It has **not** been run against your physical CWL-2-325. Start read-only, check the values, and only then enable writes. A bad gateway mode, wrong unit ID, or address offset will cause failures; writing incorrect HVAC settings can cause poor ventilation or frost-protection problems.

## 1. Configure the CWL-2-325 and Waveshare gateway

On the CWL-2-325, use the communication menu:

```text
14.1 Bus connection: Modbus
14.2 Slave address:  20
14.3 Baud rate:      19.2 kbit/s
14.4 Parity:         Even
```

Configure the Waveshare as a **Modbus TCP ↔ Modbus RTU gateway**, not as an arbitrary raw TCP serial bridge:

```text
Ethernet side: TCP server / Modbus TCP, port 502
RS485 side:    19200 baud, 8 data bits, even parity, 1 stop bit
Unit/slave ID: passed through to RTU; the Python config uses device_id 20
```

For a normal Waveshare Modbus gateway, keep this in the Python config:

```json
"transport": "modbus_tcp",
"address_offset": 0
```

`rtu_over_tcp` is included only for a gateway deliberately configured in transparent RTU-over-TCP mode. Do not select it for normal Modbus TCP conversion.

## 2. Install and make a local config

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

cp config.example.json config.json
```

Edit `config.json` and set `connection.host` to the gateway's fixed or DHCP-reserved IP address.

The CLI can also generate a fresh config and example profiles:

```bash
python wolf_cwl2.py --config config.json init-config --host 192.168.1.200
```

## 3. First test: reads only

```bash
python wolf_cwl2.py --config config.json snapshot --available-only
python wolf_cwl2.py --config config.json run --read-only --print-updates
```

Expected early checks:

- `base_software_version` and `serial_number` look plausible;
- `supply_temperature_c` and `exhaust_temperature_c` are realistic;
- `supply_airflow_actual_m3h` and `exhaust_airflow_actual_m3h` are plausible;
- `device_id` is 20;
- temperatures are not ten times too large;
- registers are not shifted by one.

The default `desired` object is empty, so a normal first run has nothing to restore. Still, `--read-only` is the safest first check.

If every value appears shifted or illegal-address errors occur for otherwise mandatory blocks, test `"address_offset": -1`. The documented CWL/UWA2 addresses and known working integrations normally use `0`, so do not change it without evidence.

## 4. Run continuously

```bash
python wolf_cwl2.py --config config.json run
```

The daemon polls live values every 5 seconds, counters/settings every 60 seconds, and identity/version data every 5 minutes. All intervals are configurable.

Each successful poll updates `wolf_state.json` atomically. A state entry has this form:

```json
{
  "value": 21.4,
  "raw": 214,
  "unit": "°C",
  "available": true,
  "updated_at": "2026-07-17T10:30:00+00:00",
  "error": null
}
```

Optional sensors or the optional UWA2-E board may return illegal-address errors. Those values are marked unavailable while the rest continue to work.

## Python API

```python
import asyncio
from wolf_cwl2 import WolfCWL2


async def main() -> None:
    controller = WolfCWL2("config.json")

    async def on_change(update: dict) -> None:
        print(update["key"], update["value"])

    controller.subscribe(on_change)
    await controller.start()

    try:
        # Cache access after the initial poll
        print(controller.get_value("supply_temperature_c"))
        print(controller.snapshot(available_only=True))

        # These writes are also stored in config.json.
        await controller.set_ventilation_level("normal")
        await controller.set_airflow(180)          # switches control mode to airflow
        await controller.set_bypass_mode("automatic")
        await controller.set_standby(False)

        # Generic named setter
        await controller.set_setting("filter_warning_days", 120)

        # Partial profile; existing desired settings not mentioned by it remain intact.
        await controller.apply_profile("night")

        # Async stream of changed values
        async for update in controller.updates():
            print(update)
    finally:
        await controller.stop()


asyncio.run(main())
```

Useful methods:

```python
await controller.start()
await controller.stop()
await controller.poll_once()
await controller.refresh("filter_status")
controller.get_value("supply_temperature_c")
controller.get_state("supply_temperature_c")
controller.snapshot(available_only=True)

await controller.set_setting(name, value)
await controller.set_settings({name: value, ...})
await controller.set_ventilation_level("holiday" | "low" | "normal" | "high")
await controller.set_airflow(0 | 50..325)
await controller.disable_remote_control()
await controller.set_standby(True | False)
await controller.set_bypass_mode("automatic" | "closed" | "open")
await controller.set_flow_presets(holiday=50, low=100, normal=175, high=300)

await controller.list_profiles()
await controller.preview_profile("night")
await controller.apply_profile("night")

await controller.reset_filter_warning()
await controller.reset_appliance(confirm=True)
```

Setters default to `persist=True`. Validation happens before the config is changed. The desired value is then written atomically to the config **before** the Modbus write. If the unit is offline, the call raises an error but the desired value remains queued in the config and will be retried by startup/reconciliation.

Use `persist=False` for a temporary change:

```python
await controller.set_ventilation_level("high", persist=False)
```

## Desired-state restoration

The config's `desired` object contains only settings that this program owns:

```json
"desired": {
  "remote_control_mode": "level",
  "remote_ventilation_level": "normal",
  "remote_standby": false,
  "bypass_mode": "automatic"
}
```

At startup, every desired register is force-written. This is intentional: the UWA2 documentation states that remote-control registers 8000-8011 and desired airflows have to be set again after mains power loss.

While running, the controller also:

- force-writes desired settings after a TCP reconnect;
- compares current holding-register values to desired values;
- rewrites mismatches when `enforce_desired_state` is enabled.

That means local touchscreen changes to an owned setting will be overwritten. Remove a key from `desired`, disable enforcement, or use a profile with `unset` when the program should stop owning a setting.

Communication registers 7990-7992, clock/date registers, and one-shot reset commands are deliberately not restorable. Changing the slave address or baud rate through the same connection can immediately cut off communication, so the normal CLI does not expose dangerous writes.

## Profiles

A profile is a separate partial JSON file in `profiles/`:

```json
{
  "description": "Quiet night ventilation",
  "settings": {
    "remote_ventilation_level": "low",
    "remote_control_mode": "level",
    "remote_standby": false
  }
}
```

Apply it:

```bash
python wolf_cwl2.py --config config.json profile night
```

Profiles are merged into the existing desired config by default. They may inherit other profiles:

```json
{
  "description": "Night ventilation with bypass open",
  "extends": ["night"],
  "settings": {
    "bypass_mode": "open"
  }
}
```

A profile can stop owning selected settings:

```json
{
  "unset": ["bypass_mode"],
  "settings": {
    "remote_ventilation_level": "normal"
  }
}
```

Set `"replace": true` to replace the entire desired object rather than merge. Cyclic inheritance, unknown settings, one-shot commands, unsafe communication settings, and invalid cross-setting relationships are rejected before any write.

## CLI examples

```bash
# Catalogue and current state
python wolf_cwl2.py registers --writable-only
python wolf_cwl2.py --config config.json get filter_status
python wolf_cwl2.py --config config.json desired
python wolf_cwl2.py --config config.json profiles
python wolf_cwl2.py --config config.json preview-profile summer-night

# Persistent changes
python wolf_cwl2.py --config config.json level high
python wolf_cwl2.py --config config.json airflow 180
python wolf_cwl2.py --config config.json bypass automatic
python wolf_cwl2.py --config config.json standby off
python wolf_cwl2.py --config config.json set filter_warning_days 120

# Temporary change, not stored/restored
python wolf_cwl2.py --config config.json level high --temporary

# One-shot commands
python wolf_cwl2.py --config config.json reset-filter
python wolf_cwl2.py --config config.json reset-appliance --yes
```

## Tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

The tests use a simulated async Modbus gateway and verify codecs, atomic persistence, profile merging, write order, and startup restoration.

## Register sources

The implementation follows:

- Brink Climate Systems, **Modbus UWA2-B/UWA2-E**, document 614882-D;
- WOLF, **CWL-2-325 installation and operating instructions**;
- PyModbus 3.14 async client API;
- Waveshare RS485-to-Ethernet Modbus gateway mode.

The unrelated Weishaupt Modbus TCP register sheet that may be in the same working directory uses a different controller, slave ID, and register map. It is not used by this project.
