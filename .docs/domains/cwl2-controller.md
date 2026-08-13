# CWL-2 controller domain

## Register catalogue

The reference catalogue defines 154 named logical values across Modbus input
and holding tables. A logical value can span one or more 16-bit words and owns
its address, table, codec, word count, scale, unit, enum labels, numeric bounds,
step, and operational flags. The package catalogue must preserve those facts
from [`wolf_cwl2.py`](../../.guides/wolf_cwl2_async/wolf_cwl2.py) and
[`REGISTER_MAP.md`](../../.guides/wolf_cwl2_async/REGISTER_MAP.md).

Operational flags have distinct meanings:

- `writable`: a named setter may write the value.
- `restorable`: the value may be stored in `desired` and reconciled later.
- `dangerous`: writing can disrupt communication or reset the appliance and
  therefore requires explicit opt-in.
- `one_shot`: a command/status register is invoked only by its dedicated method
  and is never desired state.
- `optional`: absence is expected on some sensor/UI/UWA2-E configurations.
- `poll`: `fast`, `slow`, `static`, or `never` selects normal polling behavior.

Names are canonical lower-case snake case. The aliases `fan_mode`,
`control_mode`, `fan_level`, `level`, `airflow`, `airflow_m3h`, `standby`, and
`bypass` resolve to their reference canonical settings.

## Value semantics

Decoded values are JSON-compatible engineering values, never PyModbus response
objects. Codecs cover unsigned/signed 16-bit values, scaled unsigned/signed
values, unsigned 32-bit counters, enums, booleans, version strings, a 12-digit
BCD serial, packed date/time components, raw words, CWL-325 airflow/PWM rules,
and the asymmetric standby register. Unknown enum words decode as
`unknown_<raw>` so a new device value is observable rather than discarded.

Register 8003 is asymmetric: writes use `1` for standby and `2` for normal,
while reads expose state `1`/`0`. Equality and read-back verification compare
the decoded boolean state.

Cross-setting validation preserves these relationships:

- holiday, low, normal, and high airflow presets are nondecreasing;
- supply PWM presets and exhaust PWM presets are independently nondecreasing;
- each CO2 low threshold does not exceed its high threshold;
- each analog input minimum does not exceed its maximum;
- the ground heat-exchanger minimum temperature is strictly below its maximum.

When an individual or partial change touches one of these groups, every omitted
peer is refreshed from the device before persistence. The complete confirmed
candidate is then validated; an unavailable peer or invalid relationship fails
before desired-state mutation or Modbus writes. Complete submitted groups need
no peer preflight reads beyond normal write verification.

The detailed per-register limits and enums belong to the package catalogue data,
not this prose record.

## State and updates

Each catalogue key has a cached state containing `value`, `raw`, `unit`,
`available`, `updated_at`, and `error`. State becomes available after successful
decoding. A protocol rejection or decode error preserves an observable error and
marks the value unavailable. Changes emit a dictionary containing `key` plus the
state fields to synchronous/async callbacks and async iterator subscribers.

Some appliances represent an absent optional extension value with a successful
function response containing zero data words. When the connection remains
healthy, this is treated as optional unavailability. Optional block reads first
fall back to individual definitions so supported neighbors remain available.

Snapshots contain connection status and generation, the last connection error,
per-tier poll timestamps, last profile, desired state, all selected value states,
and a UTC generation timestamp. Queue backpressure drops the oldest queued
update rather than blocking Modbus work.

## Polling and connection lifecycle

Documented addresses are grouped into non-overlapping fast, slow, and static
read blocks. Default intervals are 5, 60, and 300 seconds. Holding and extension
blocks can be disabled independently. One-shot reset/status registers have
`poll=never` and are read explicitly only when their command flow requires it.

All requests through one client are serialized. A protocol exception for an
optional block does not invalidate the TCP connection; it marks that block
unavailable and polling continues. No-response, socket, timeout, or PyModbus
transport failures close the client and are retried. Each successful new client
connection increments the connection generation.

## Desired state and writes

Named writes validate and normalize all changes before any persistence or I/O.
Persistent settings are written atomically to the configuration before device
I/O. Therefore an offline write raises an error while deliberately retaining
the desired value for later restoration. Bulk writes report successful results
and per-key errors.

Write order handles ordinary settings first in stable address/name order, then
places target values before the mode that activates them:
`remote_ventilation_level` and `remote_airflow_m3h`, then `remote_standby`, then
`remote_control_mode`.
Normal writes use configured read-back verification and numeric tolerance based
on register scale. Dangerous communication writes skip verification because the
write may immediately sever the connection.

At startup, desired values are force-written when configured. A new connection
generation can also trigger a force-write. Periodic reconciliation optionally
rewrites only mismatches. Read-only mode disables restoration, reconciliation,
and all writes.

Filter reset is a non-dangerous one-shot command. Appliance reset requires
`confirm=True`, sends its one-shot command, and closes the connection because
the unit may reboot. Neither belongs in desired state.

## Profiles

Profiles are named JSON files relative to `profiles_dir`. They contain optional
`description`, `extends` (one name or an ordered list), `settings`, `unset`, and
`replace`. Parent profiles resolve first; child settings override them, and an
unset key removes inherited or existing ownership. Merge is the default;
`replace: true` replaces the entire desired object. Profile names are limited to
letters, digits, `_`, `.`, and `-`; resolution rejects path escape, missing
files, cycles, unknown/non-restorable settings, and invalid cross-setting state
before any write.

Persistent desired state can be captured back into a profile. At capture time,
`last_profile` is an optional parent: its fully resolved settings are compared
with canonical desired ownership, changed/new desired keys become `settings`,
and parent keys no longer owned become `unset`. The parent's `replace` flag is
preserved so the saved child resolves and applies with the same replacement
semantics. Without a parent, the complete nonempty desired mapping becomes a
standalone profile. Temporary writes do not change desired ownership and are
not captured. A persistently applied profile sets `last_profile`, and subsequent
persistent edits/releases retain it so those changes can be saved as its child.

Capture is descriptive, not an apply operation. Saving writes the derived JSON
atomically after validating names, inheritance, desired settings, nonempty
delta, and collision policy. It does not change device state, desired state,
`last_profile`, or the active controller lifecycle. See the [profile capture
workflow](../workflows/profile-capture.md).
