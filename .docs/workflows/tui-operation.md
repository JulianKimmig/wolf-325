# Textual TUI operation

## Launch safely

The interactive interface is the `wolf-cwl2-tui` console command. It uses the
same schema-version-1 configuration, controller, register catalogue, profiles,
desired state, and state persistence as `wolf-cwl2`.

Start with passive monitoring:

```bash
uv run wolf-cwl2-tui \
  --config wolf_cwl2_config.json \
  --read-only
```

Read-only mode leaves refresh and navigation available while disabling edit,
desired-state release/application, profile apply, and profile capture. The TUI
also passes read-only mode into `WolfCWL2`, providing a service-level guard even
if an action is invoked without its disabled button.

After validating the connected appliance and reviewing the configuration's
`desired` values, omit `--read-only` to enable control:

```bash
uv run wolf-cwl2-tui --config wolf_cwl2_config.json
```

TUI startup deliberately skips startup restoration. Control-enabled background
mode still runs configured reconciliation, which can enforce persistent desired
values and restore them after reconnect. Use `--read-only`, an empty `desired`
object, or release individual desired keys when the session must remain passive.

## Navigate and inspect

The left tree contains quick views for overview, all registers, writable
registers, and problems; monitor/settings domain sections; and the current
desired-state view. The all-register view accounts for all 154 catalogue keys,
including unavailable optional hardware and one-shot status registers.

The center table shows description, decoded value, unit, state, flags, and last
update. Selecting a row shows its canonical name, wire metadata, codec,
validation constraints, raw/current values, desired ownership, and error in the
right detail panel. Search matches all entered tokens across operator-facing
metadata, addresses, states, flags, and errors.

Useful keys are:

- `/`: focus search;
- Escape: return focus to values;
- `r`: explicitly refresh the selected register;
- `e`: edit or execute the selected writable register;
- `p`: open profiles;
- `s`: preview and save persistent desired changes as a profile;
- `q`: stop the controller and quit.

`--refresh-interval` controls how often cached snapshots redraw on screen. It
does not accelerate Modbus polling. Use `r` for an immediate device read; when
no row is selected, refresh polls the configured tiers once.

## Write and desired ownership

Editors reflect canonical register metadata. Enum and boolean values are
selected, numeric/packed values are entered, and validation occurs before the
controller writes. For restorable settings, `Persist and reconcile` defaults to
enabled:

- enabled writes the normalized value to config first and makes the controller
  own/reconcile it;
- disabled performs a temporary write without adding desired ownership; and
- `Release desired` removes ownership without sending a replacement value.

`Apply desired` force-writes every currently owned desired value. Profile
selection previews resolved inheritance, replace behavior, released keys, and
settings before application; its persistence switch chooses whether results
become desired state.

`Save profile`/`s` performs the reverse persistence workflow: it previews
changes from current persistent desired ownership relative to the optional
`last_profile`, then accepts a name, description, and explicit overwrite
choice. A persistently applied base profile remains the parent across later
persistent edits and releases. Temporary writes are absent from this preview.
The resulting profile is saved but not selected, applied, or added to desired
state. See [profile capture](profile-capture.md) for delta and guard details.

Wait for the activity log/notification to report completion before starting a
second controller or profile-file operation. Operation errors remain visible in
the log, and the table/details refresh from current controller state.

## Dangerous operations

Unlike the standard CLI, the TUI exposes every catalogue register marked
writable, including communication settings and reset commands. Confirmation
phrases are exact and case-sensitive:

- filter reset: `EXECUTE ACTION`;
- appliance reset: `RESET APPLIANCE`;
- Modbus interface/address/speed and other dangerous writes:
  `APPLY DANGEROUS WRITE`.

Communication writes are not persistent and may immediately disconnect the
active gateway session; controller verification is intentionally skipped for
them. Appliance reset can restart the unit and close the client. Confirm the
current gateway/unit configuration and recovery path before executing either.
The activity log confirms dispatch, not that a disconnected appliance completed
its physical transition.

## Shutdown

Use `q` for normal shutdown. The application stops background controller tasks,
closes the transport, and writes the final configured state snapshot through the
normal controller lifecycle. Do not terminate the process during a write merely
because the UI redraw interval has elapsed; redraw cadence is independent of
device-operation completion. Timer callbacks already queued during teardown are
ignored once the default screen is unmounted, so they cannot query removed
widgets or obscure clean controller shutdown.
