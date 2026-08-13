# Async WOLF CWL-2-325 controller

`wolf-325` is a Python 3.11+ async Modbus controller for a WOLF CWL-2-325
ventilation appliance connected through a Waveshare RS485-to-Ethernet gateway.
The repository contains both the reusable Python client and its native Home
Assistant custom integration.

The package provides:

- all 154 documented UWA2-B/UWA2-E input and holding values;
- fast, slow, and static polling with an in-memory cache;
- synchronous/async callbacks and an async update iterator;
- validated named setters, persistent desired state, and read-back verification;
- startup/reconnect restoration and periodic reconciliation;
- composable partial JSON profiles with inheritance, replacement, and unset;
- guarded filter/appliance reset commands;
- atomic JSON config/state persistence;
- a CLI for configuration, reads, writes, profiles, and daemon operation; and
- a full-screen TUI for live monitoring and guarded interactive control.

## Install

Install the published client with uv:

```bash
uv tool install "wolf-325[tui]==0.1.1"
wolf-cwl2 --help
wolf-cwl2-tui --help
```

For repository development:

```bash
uv sync --group dev
uv run wolf-cwl2 --help
```

The base runtime installs PyModbus only. Textual is isolated in the `tui`
optional extra; the development group installs it for the terminal interface
and its tests. For a package installation outside this repository, select
`wolf-325[tui]` when the TUI is required.

The console command and module entry point are equivalent:

```bash
uv run wolf-cwl2 registers --writable-only
uv run python -m wolf_325 registers --writable-only
```

## Home Assistant integration

The repository contains a native `wolf_cwl2` custom integration for Home
Assistant. It creates one config entry and device per verified appliance serial,
supports multiple appliances from the first release, polls automatically for
Recorder history, exposes the complete reviewed datapoint/control surface, and
stores profiles independently in Home Assistant.

Release status: the integration is fully exercised in the local Home Assistant
2026.2.3 test host. The lightweight
[`wolf-325==0.1.1`](https://pypi.org/project/wolf-325/0.1.1/) client is published
on PyPI and pinned exactly by integration version `0.1.2`. The public repository
passes both HACS repository validation and Home Assistant hassfest. The project
is licensed under MIT with Julian Kimmig as author, copyright holder, and
GitHub code owner.

For repository development:

```bash
uv sync --group dev
UV_CACHE_DIR=.cache/uv uv run pytest \
  -c tests/components/wolf_cwl2/pytest.toml \
  -p no:sugar tests/components/wolf_cwl2
```

### Install through HACS

1. Open **HACS → Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/JulianKimmig/wolf-325` with category
   **Integration**.
4. Select **WOLF CWL-2**, choose **Download**, and restart Home Assistant.

HACS installs the integration from the repository's default `main` branch.
After restarting, add the integration through Home Assistant as described
below.

For a manual installation, copy only `custom_components/wolf_cwl2` into the
Home Assistant configuration directory's `custom_components/` folder and
restart Home Assistant. Home Assistant installs the exact client requirement
from PyPI while loading the integration.

### Add appliances and choose authority

In Home Assistant, open **Settings → Devices & services → Add integration** and
select **WOLF CWL-2**. Enter the gateway host/port, Modbus unit ID, transport
(`modbus_tcp` or `rtu_over_tcp`), and address offset (`0` normally, `-1` only for
a gateway that maps one-based addresses). Setup performs a read-only identity
probe. The verified 12-digit serial is the stable identity, so moving a gateway
does not replace Recorder history. Add each additional appliance as a separate
entry; duplicate serials are rejected.

Entry options provide three authority modes:

- `monitor_only`: polling and read entities only; every control/action rejects
  before Store or Modbus mutation.
- `temporary`: safe controls and profile application change the live appliance
  but create no durable desired ownership.
- `persistent`: desired values are stored before I/O and reconciled after drift
  or reconnect. Failed writes remain queued.

Leaving persistent mode keeps desired values dormant. Returning does not
silently reassert them: use **Resume desired ownership** to authorize a forced
apply, or **Clear desired ownership** to release them without changing the
current appliance values.

Fast, slow, static, and reconciliation intervals are configurable integer
seconds with a five-second floor. Defaults are 5, 60, 300, and 30 seconds.
Holding-register and optional-extension polling can be disabled independently.

### Entities, Recorder, and controls

The integration classifies all 154 catalogue keys: 83 sensors, 39 numbers, 20
selects, 10 switches, and two guarded action-only reset values. Thirty-six
ordinary entities are enabled by default; advanced and diagnostic entities stay
available in the entity registry but begin disabled. The normal curated read
surface contains 23 sensors.

Sensor state is confirmed cached device state. Polling, disconnect, and stale
tier handling drive entity availability; volatile raw words, errors, desired
values, and profile lineage are not entity attributes. Instantaneous proven
telemetry uses Recorder measurement metadata where legal. Counters do not claim
total/total-increasing statistics until their reset/monotonic behavior is
physically proven.

Safe numbers, selects, and switches remain visible in every authority mode so
dashboards and automations keep stable entity IDs. Monitor-only calls reject;
temporary calls write without ownership; persistent calls store desired state
before verified device I/O. Appliance clock and Modbus interface/address/baud
settings remain read-only. There is no raw-register service.

### Home Assistant profiles

The synthetic **Profile** select lists the profiles in that entry's private
Home Assistant Store. Selecting a profile applies it under the current
authority contract. Its state is the last profile Home Assistant fully applied,
not a claim that live settings still match. Profile writes are sequential and
not device-atomic: partial success is not rolled back, and persistent desired
values stay queued for reconciliation.

Use the response-capable `wolf_cwl2.preview_profile_capture` action to inspect
the exact persistent desired-state delta, parent lineage, `unset` list, and
Store revision. Use `wolf_cwl2.save_profile` with a suffix-free `name`, optional
`description`, explicit `overwrite`, and optionally the previewed
`expected_revision`. Capture is persistent-only, performs no Modbus I/O, and
never includes temporary writes or live telemetry. Saving neither applies nor
selects the new profile.

```yaml
action: wolf_cwl2.save_profile
data:
  config_entry_id: "<entry-id>"
  name: custom-night
  description: Quiet settings derived from the active base profile
  overwrite: false
  expected_revision: 12
```

### Guarded actions, diagnostics, and recovery

`wolf_cwl2.reset_filter` requires one loaded entry, temporary/persistent mode,
a fresh serial match, and confirmation `EXECUTE ACTION`. Appliance reset has no
entity and additionally requires the disabled-by-default entry opt-in, a Home
Assistant administrator context, and confirmation `RESET APPLIANCE`. Its
response means only `command_sent`; cached availability is invalidated and
ordinary polling reconnects. Neither reset changes desired/profile Store state.

Download integration or device diagnostics through Home Assistant for versions,
non-sensitive policy, scheduler/connection health, tier freshness, and
availability/error counts. The download excludes endpoints, identity, live/raw
values, desired/profile content, and exception text. Persistent Repairs are
created only for changed identity, invalid Store data, or a newer unsupported
Store schema—not for an ordinary disconnect.

Reconfigure an entry to move its gateway while retaining serial identity and
Recorder history. Reload drains in-flight work and replaces only that entry's
runtime. Removing an entry closes its transport and permanently deletes only
its Home Assistant-owned desired state, lineage, and profiles; it does not write
or reset the appliance.

## Interactive TUI

Start the full controller interface with the same JSON configuration:

```bash
uv run wolf-cwl2-tui --config wolf_cwl2_config.json
```

For an initial inspection that cannot write the device or configuration:

```bash
uv run wolf-cwl2-tui \
  --config wolf_cwl2_config.json \
  --read-only
```

The left tree groups every documented register into monitor and settings
submenus. Quick views cover the live overview, all registers, writable values,
errors, and persistent desired state. Search matches words across keys,
descriptions, Modbus addresses, status, and errors. The right panel shows wire
address, codec, limits, raw value, poll tier, timestamps, ownership, and safety
flags for the highlighted value.

Use `e` or **Edit / execute** for metadata-derived enum, boolean, numeric,
date/time, or one-shot editors. Restorable settings can be persistent or
temporary. Communication changes and appliance reset require exact confirmation
phrases because they can disconnect the active session. Profiles are always
resolved and previewed before application. Use `s` or **Save profile** to review
and save persistent desired-state changes as a new profile; when a profile was
loaded, the saved profile extends it. The TUI skips the immediate startup
restore, but control-enabled mode still follows the configured periodic and
reconnect desired-state reconciliation policy. Use `--read-only` for a fully
passive session, or **Apply desired** for an immediate explicit reconciliation.

## Connected gateway

The repository's physical Waveshare gateway endpoint is intentionally kept in
the local untracked config. Its verified configuration is:

```text
Ethernet: TCP server, Modbus TCP-to-RTU, port 502
RS485:    19200 baud, 8 data bits, even parity, 1 stop bit
Device:   Modbus unit/slave ID 20
Offset:   0
```

The web interface remains on port 80. Keep its password outside source,
snapshots, reports, and issue text.

On the CWL-2-325, communication menu 14 should match:

```text
14.1 Bus connection: Modbus
14.2 Slave address:  20
14.3 Baud rate:      19.2 kbit/s
14.4 Parity:         Even
```

These values follow Brink's official
[Modbus UWA2-B/UWA2-E 614882-D documentation](https://www.brinkclimatesystems.nl/documenten/modbus-uwa2-b-uwa2-e-installation-regulations-614882.pdf).

## Configure and read safely

Create a local configuration and example profiles:

```bash
uv run wolf-cwl2 \
  --config wolf_cwl2_config.json \
  init-config --host <gateway-host>
```

Generated local config/state files are ignored by Git. A fresh configuration
has an empty `desired` object and therefore owns no device settings.

Start with read-only commands:

```bash
uv run wolf-cwl2 --config wolf_cwl2_config.json snapshot --available-only
uv run wolf-cwl2 --config wolf_cwl2_config.json get supply_temperature_c
uv run wolf-cwl2 --config wolf_cwl2_config.json get supply_dew_point_c
uv run wolf-cwl2 \
  --config wolf_cwl2_config.json \
  run --read-only --print-updates
```

Expected checks include plausible software/hardware versions, a 12-digit serial,
unit address 20, realistic temperatures/airflows/fan speeds, and no one-word
address shift. The physical device returns a connected zero-word response for
the absent optional `extension_hardware_version`; the library isolates it as
unavailable while preserving neighboring extension values.

## Python API

```python
import asyncio

from wolf_325 import WolfCWL2


async def main() -> None:
    controller = WolfCWL2("wolf_cwl2_config.json")

    async def on_change(update: dict) -> None:
        print(update["key"], update["value"])

    controller.subscribe(on_change)
    await controller.start(read_only=True)
    try:
        print(controller.get_value("supply_temperature_c"))
        print(controller.snapshot(available_only=True))
    finally:
        await controller.stop()


asyncio.run(main())
```

Core read/cache methods:

```python
await controller.start()
await controller.stop()
await controller.poll_once()
await controller.refresh("filter_status")
controller.get_value("supply_temperature_c")
controller.get_state("supply_temperature_c")
controller.get_value("supply_dew_point_c")
controller.snapshot(available_only=True)
```

Validated writes are available after values have been reviewed against the
physical installation:

```python
await controller.set_ventilation_level("normal")
await controller.set_airflow(180)
await controller.set_bypass_mode("automatic")
await controller.set_standby(False)
await controller.set_setting("filter_warning_days", 120)
await controller.apply_profile("night")
await controller.save_profile("custom-night", description="Night with 120-day filter interval")
```

Setters default to `persist=True`. The normalized desired value is written to
the config before Modbus I/O, so an offline write remains queued for startup or
reconnect restoration. Use `persist=False` for a temporary change.

## Profiles and CLI writes

Example profiles are generated under the configured `profiles_dir`:

```bash
uv run wolf-cwl2 --config wolf_cwl2_config.json profiles
uv run wolf-cwl2 --config wolf_cwl2_config.json preview-profile night
uv run wolf-cwl2 --config wolf_cwl2_config.json profile night
uv run wolf-cwl2 \
  --config wolf_cwl2_config.json \
  save-profile custom-night --description "My adjusted night profile"
```

`save-profile` is local-only: it does not connect to or write the appliance. It
compares persistent `desired` state with the last loaded profile, writes only
changed/new settings plus released parent settings, and sets `extends` to that
parent. Without a loaded profile it writes all desired settings as a standalone
profile. Temporary writes are intentionally excluded. Existing files are
protected unless `--overwrite` is supplied, and saving does not activate the
new profile or change desired state.

Other write commands include:

```bash
uv run wolf-cwl2 --config wolf_cwl2_config.json level high
uv run wolf-cwl2 --config wolf_cwl2_config.json airflow 180
uv run wolf-cwl2 --config wolf_cwl2_config.json bypass automatic
uv run wolf-cwl2 --config wolf_cwl2_config.json standby off
uv run wolf-cwl2 --config wolf_cwl2_config.json set filter_warning_days 120
```

Add `--temporary` to supported commands to avoid persistent ownership. Appliance
reset requires `reset-appliance --yes`; communication registers are deliberately
not exposed as normal CLI writes.

## Tests and physical audit

Run the complete simulated suite and branch-aware coverage:

```bash
uv run pytest
uv run pytest --cov=wolf_325 --cov-branch --cov-report=term-missing
```

The physical audit is opt-in and read-only. It reads every catalogue definition
individually—including the two normal `poll="never"` reset-status values—and
then verifies normal block polling:

```bash
WOLF_325_DEVICE_CONFIG=/path/to/local-device-config.json \
WOLF_325_DEVICE_REPORT=/tmp/wolf-325-device-audit.json \
uv run pytest -m hardware tests/hardware/test_read_all.py
```

The verified 2026-07-18 run accounted for all 154 definitions: 153 available,
one unsupported optional, zero decode errors, zero failed keys, and zero required
failures. The raw report is intentionally untracked because it contains the
device serial and live operational data.

## License

This project is licensed under the [MIT License](LICENSE). Copyright (c) 2026
Julian Kimmig.
