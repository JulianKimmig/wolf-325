# Controller API and JSON contracts

This record defines the compatibility surface being ported from the external
guide into the installed `wolf_325` package. Domain semantics are in
[`cwl2-controller.md`](../domains/cwl2-controller.md).

## Python surface

[`wolf_325.__init__`](../../src/wolf_325/__init__.py) is the stable import
surface. It exposes `WolfCWL2`, the register catalogue/lookup types needed by
callers, `DEFAULT_CONFIG`, profile result types `ResolvedProfile`,
`ProfileChanges`, and `SavedProfile`, and the public exception hierarchy: `WolfError`,
`ConfigError`, `ProfileError`, `RegisterError`, `ValidationError`,
`CommunicationError`, `RemoteModbusError`, `VerificationError`, and
`BulkWriteError`. Internal module placement may change without changing these
exports.

`WolfCWL2(config_path="wolf_cwl2_config.json")` preserves file-backed CLI/TUI
behavior. `WolfCWL2.from_config(config, save_callback=...,
profile_repository=...)` is the host-neutral construction path: it requires no
configuration/profile/state files and awaits host persistence callbacks before
publishing desired mutations. Both support async context-manager use and these
behavioral groups:

- lifecycle/read: `load_config`, `start`, `stop`, `poll_once`, `refresh`,
  `connected`, `desired`, `get_value`, `get_state`, and `snapshot`;
- updates: `subscribe`, returning an unsubscribe callable, and `updates`, an
  async iterator;
- writes: `set_setting`, `set_settings`, `set_ventilation_level`, `set_airflow`,
  `disable_remote_control`, `set_standby`, `set_bypass_mode`, and
  `set_flow_presets`;
- profiles: `list_profiles`, `preview_profile`, `apply_profile`,
  `preview_profile_changes`, and `save_profile`;
- lifecycle commands: `apply_desired`, `reset_filter_warning`, and the guarded
  `reset_appliance(confirm=True)`.

Setters default to `persist=True`; temporary calls use `persist=False`.
`refresh(name)` returns the decoded value (or `None`), while `get_state(name)`
returns the complete state dictionary. `updates` accepts the keyword-only
`queue_size` argument, defaulting to 200.
`set_settings` returns a mapping from canonical names to read-back/current
values. `apply_desired` returns `written`, `skipped`, and `errors` mappings.
When a bulk write raises, including after a communication failure,
`BulkWriteError` exposes partial `results` and `errors` mappings; with
`raise_on_error=False`, its return mapping contains successful keys only.
`reset_appliance(confirm=True)` returns a command-sent message and closes the
client without attempting a read-back that could race the appliance reboot.
`preview_profile_changes()` and `save_profile()` are local profile operations;
they do not require controller startup or device connectivity.

`start(initial_poll=True, restore=..., background=..., read_only=...)` retains
the historic initial poll by default. Embedded schedulers pass
`initial_poll=False`, `restore=False`, and `background=False` so exactly one
host-owned first poll and periodic owner exist.

## Configuration schema version 1

The top-level JSON object contains:

| Key | Meaning |
|---|---|
| `schema_version` | Must equal `1`. |
| `connection` | Gateway/client settings: `host`, `port`, `device_id`, `address_offset`, `transport`, timeouts, retries, and reconnect delays. |
| `polling` | Fast/slow/static/reconcile intervals and holding/extension enable flags. |
| `persistence` | Startup/reconnect restoration, enforcement, and read-back verification settings. |
| `profiles_dir` | Profile directory, resolved relative to the config file unless absolute. |
| `state_file` | Snapshot path, resolved relative to the config file unless absolute; an empty/null value disables it. |
| `desired` | Canonical, restorable named settings owned by the controller. |
| `last_profile` | Last persistently applied profile name or `null`. |

Missing nested fields are deep-merged with `DEFAULT_CONFIG`; unknown schema
versions are rejected. Host is non-empty, port is 1..65535, device ID is
1..247, address offset is `0` or `-1`, and transport is `modbus_tcp` or
`rtu_over_tcp`. Poll/reconcile intervals are positive and verification attempts
are at least one. `desired` is normalized and must contain only restorable,
non-one-shot, non-dangerous settings.

Configuration writes are atomic replacement writes in the destination
directory. The file is flushed before replacement; partial JSON must not become
the visible configuration. Filesystem calls execute outside the event-loop
thread. `RuntimeConfigStore` applies the same schema/default/desired validation
without paths and awaits its host save callback before updating visible state.

## Profile schema

A profile is a top-level JSON object with these fields:

```json
{
  "description": "optional text",
  "extends": ["parent"],
  "settings": {"remote_ventilation_level": "low"},
  "unset": ["bypass_mode"],
  "replace": false
}
```

`extends` may also be one string. `settings` defaults to an empty object,
`unset` to an empty list, and `replace` to false. Resolution returns the profile
name, description, normalized settings, normalized unset names, replacement
flag, and ordered/deduplicated source names.

### Captured profile documents

Profile capture uses the controller's canonical persistent `desired` mapping,
not cached/live device values. Temporary writes and temporary profile
applications are therefore excluded. If `last_profile` is a name at capture
time, that fully resolved profile is the single `extends` parent; if it is
`null`, the capture is standalone and omits `extends`.
Persistently applying a profile sets this marker, and later persistent
setting changes or releases preserve it for derivation.

Relative to the resolved parent, `settings` contains canonical desired keys
that are new or changed and `unset` contains parent keys absent from desired.
Both are deterministically key-sorted. A standalone capture stores the complete
desired mapping in `settings` and an empty `unset`. The emitted `replace` equals
the parent profile's resolved `replace` flag, or false for a standalone capture.
The document always contains `description`, `replace`, `settings`, and `unset`.

`preview_profile_changes()` returns `ProfileChanges(extends, settings, unset,
replace)` without applying the empty-delta guard. `save_profile(name,
description="", overwrite=False)` validates a suffix-free name and atomically writes
`<profiles_dir>/<name>.json`, returning `SavedProfile` with name, path,
description, and the exact changes. A non-filesystem repository returns
`path=None`. Save rejects an invalid name, a missing or
invalid parent, self-extension, a delta with neither settings nor unset, and an
existing target unless overwrite is explicit. Desired values are normalized as
restorable settings before diffing. Saving neither activates the new profile nor
changes `desired` or `last_profile`.

`ProfileRepository` owns common graph resolution/capture/save behavior.
`ProfileLoader` supplies filesystem documents and `MemoryProfileRepository`
supplies isolated host-owned documents with an awaited save callback. Candidate
overwrite validates the complete profile graph, including descendants, before
commit.

The full procedure and operator cautions are in the [profile capture
workflow](../workflows/profile-capture.md).

## State and update JSON

A value state has exactly these semantic fields:

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

An update adds `key` to this shape. A snapshot contains `connected`,
`connection_generation`, `last_connection_error`, `last_poll_at`,
`last_profile`, `desired`, `values`, and `generated_at`. Timestamps are UTC ISO
8601 strings. `snapshot(available_only=True)` filters only `values`; it does not
alter the surrounding metadata.

For an optional definition that returns a connected zero-word response,
`refresh(name)` returns `None` and `get_state(name)` reports
`available: false` with a `short response` error. Required definitions retain
strict short-response failures.

## CLI surface

The `wolf-cwl2` console script declared in [`pyproject.toml`](../../pyproject.toml)
and [`python -m wolf_325`](../../src/wolf_325/__main__.py) dispatch to the same
CLI. It accepts `--config` and `--log-level` plus these reference-compatible
subcommands: `init-config`, `run`, `snapshot`, `get`, `set`, `level`, `airflow`,
`standby`, `bypass`, `profiles`, `preview-profile`, `profile`, `save-profile`, `desired`,
`registers`, `reset-filter`, and `reset-appliance`.

Read commands (`snapshot` and `get`) do not restore desired state. `run
--read-only` disables all writes. Dangerous generic writes are not exposed by
the normal CLI; appliance reset requires `--yes`. Successful commands return
zero, handled domain errors return two, and keyboard interruption returns 130.

`save-profile NAME [--description TEXT] [--overwrite]` is a config-local
command. It loads configuration and profile files without starting the
controller or opening Modbus. On success it prints JSON containing `name`,
`path`, `description`, `extends`, `replace`, `unset`, and `settings`. The normal
CLI has no global read-only mode for local commands; collision replacement is
controlled only by explicit `--overwrite`. The command does not activate or
apply the saved profile.

## Textual operator surface

[`pyproject.toml`](../../pyproject.toml) exposes the separate `wolf-cwl2-tui`
entry point backed by [`tui.py`](../../src/wolf_325/tui.py). It accepts:

| Option | Contract |
|---|---|
| `--config PATH` | Controller configuration; defaults to `wolf_cwl2_config.json` and is expanded/resolved before application construction. |
| `--read-only` | Disables register writes, desired release/application, profile application, and profile-file capture in both controls and service guards. |
| `--refresh-interval SECONDS` | Positive cached-snapshot redraw interval; defaults to 1.0 seconds and does not change controller polling intervals. |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, or `ERROR`; defaults to `WARNING`. |

The TUI owns its controller lifecycle. It starts with `restore=False`, so it
does not perform startup restoration. Normal control-enabled background mode
still runs controller polling and reconciliation according to configuration;
read-only mode suppresses reconciliation and every mutation. Unmounting stops
the controller and closes/persists through the normal controller path.

The opening overview contains high-signal live and remote-control values.
Navigation also exposes all registers, all writable registers, current problem
states, current desired-state ownership, and monitor/settings sections. The
section taxonomy must assign every catalogue key exactly once. Rows retain
unavailable definitions and show value, unit, live/waiting/error state,
writable/desired/danger/action flags, and last-update time. Search is
case-insensitive, splits input into tokens, and requires every token to match
combined key, description, address, table, unit, state, error, or flag text.

The details panel displays canonical key, description, table/address/count,
codec, polling tier, unit, validation range/enums, active capabilities, current
and raw values, timestamp, desired value when owned, and last error. Editors are
derived from `RegisterDef`: enums and booleans use selections, packed values use
text, other numeric values use input, and one-shot registers use action dialogs.
All submitted values pass through canonical normalization before service and
controller validation.

Restorable editors offer a `Persist and reconcile` switch, enabled by default;
non-restorable and one-shot operations are temporary. Releasing a desired key
removes controller ownership without writing a replacement value. Profile
selection shows the fully resolved description, sources, replace flag, unset
keys, and settings before application; persistence is operator-selectable.
`Save profile` previews the current persistent delta's optional base,
replacement policy, settings, and releases, then accepts a required name,
optional description, and an overwrite switch that defaults off. Saving is
disabled and service-rejected in read-only mode. It creates a profile file only;
it does not apply the profile or change desired ownership.

Dangerous and one-shot operations require exact, case-sensitive phrases:

- `EXECUTE ACTION` for the filter-reset action;
- `RESET APPLIANCE` for appliance reset; and
- `APPLY DANGEROUS WRITE` for other dangerous registers, including Modbus
  communication settings that may disconnect the session.

Interactive controller and profile-file jobs use the `device` worker group with
exclusive execution.
Failures are reported in the activity log and an error notification, after
which the snapshot and table are redrawn. Keyboard bindings are `q` quit, `/`
focus search, `r` refresh selected, `e` edit/execute selected, `p` profiles, `s`
save current persistent changes as a profile, and Escape return focus to the
value table. Normal TUI shutdown returns status zero.
