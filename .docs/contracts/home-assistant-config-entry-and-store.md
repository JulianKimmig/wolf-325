# Home Assistant config-entry and Store contract

## Config entry

The integration domain is `wolf_cwl2`. Entry version 1.2 uses the verified
12-digit appliance serial as `unique_id` and stores mutable connection facts in
`data`. Runtime policy belongs in `options`. Secrets are not currently part of
the Modbus TCP contract. The real 1.1-to-1.2 migration adds only the
disabled-by-default appliance-reset opt-in; it does not open the device or
change connection facts.

Required connection data:

- `host`
- `port`
- `device_id`
- `transport`
- `address_offset`

Required policy options:

- `authority`: `monitor_only`, `temporary`, or `persistent`
- `fast_interval_seconds`
- `slow_interval_seconds`
- `static_interval_seconds`
- `reconcile_interval_seconds`
- `allow_appliance_reset`

Intervals are integer seconds at or above five. Validation rejects invalid
values rather than substituting defaults or clamping.

Default policy is `monitor_only`, with 5-second fast, 60-second slow,
300-second static, and 30-second reconciliation intervals. Holding-register and
optional-extension polling both default enabled.
The appliance-reset opt-in defaults false and is required in addition to the
action's authority, administrator, confirmation, and live-identity gates.

## Configuration and identity probe

User setup validates host, port 1–65535, device ID 1–247, transport
`modbus_tcp`/`rtu_over_tcp`, and address offset 0/-1. It then constructs the
public client with restoration, background scheduling, initial polling, and
client-owned state output disabled. The probe reads only `serial_number` and
`appliance_type`, closes transport on every outcome, and performs no write.

A valid non-zero 12-digit serial becomes the entry unique ID. A duplicate
serial aborts even when endpoint facts differ; different serials create
independent entries. Connection failure and invalid identity keep the form open
with distinct errors.

Reconfigure pre-fills current endpoint data, repeats the same live read-only
probe, and updates/reloads only when the serial matches the existing unique ID.
A mismatch aborts without changing entry data. Options use
`OptionsFlowWithReload`; the integration does not add an update listener, so
one successful options change schedules exactly one targeted reload.

## Runtime data

`ConfigEntry.runtime_data` holds a typed entry runtime containing the public
controller, Store/profile adapters, operation lock, and coordinator. It is
created only during successful setup and cleared during unload. No module-global
controller, scheduler, desired state, or profile state is permitted.

The runtime also records authority, stopping state, and the retained scheduler
unsubscribe callback. The coordinator publishes immutable snapshot/tier-success
data with `always_update=False`. Entity properties read only the controller
cache. Global update failure, disconnected transport, stale tier, or unavailable
value makes the initial airflow entity unavailable.

## Store

One versioned private Store document exists per config entry. Its storage key is
`wolf_cwl2.<entry_id>` and never includes the network endpoint. The Home
Assistant Store wrapper and integration payload both use major version 2.
The payload contains:

- `schema_version` and a monotonically increasing `revision`;
- canonical persistent `desired` settings;
- optional `last_profile` lineage;
- optional `last_applied_profile` truth for the profile selector;
- `desired_active` authorization and the last loaded authority mode;
- portable profile documents; and
- an `examples_seeded` marker.

The current implementation stores desired, lineage, last-successful profile,
active/dormant authorization, last authority, and the complete profile
catalogue in one revisioned payload. Canonical example profiles seed only a new
Store and are never reapplied to an existing document.

Leaving persistent mode sets `desired_active=false` while retaining desired and
lineage. Returning to persistent preserves dormancy when retained desired values
exist. A first persistent entry with no desired state activates safely. Resume
and clear are explicit durable button operations; clear removes ownership
without writing replacement device values.

Save operations are serialized and immediate; delayed Store writes are not
used. After `Store.async_save`, the transaction owner reloads through the
public Store API and requires exact next-revision equality before changing its
visible payload. This detects Store write failures that Home Assistant logs but
does not raise. Profile overwrite validates the complete prospective
inheritance graph before committing one replacement document. Profile markers
must name existing documents.

Profile preview returns exact shared-engine delta, lineage, replace flag,
change flag, and current Store revision. Save may require that revision; a stale
value fails before catalogue mutation. Successful capture changes one profile
document, increments the Store revision once, refreshes runtime profile options,
and leaves desired, lineage, last-applied selection, and device state unchanged.

The real wrapper/payload v1-to-v2 migration preserves desired state, lineage,
last-successful profile, examples, and profile documents, increments the
integration revision once, and adds `desired_active=false` plus
`last_authority=null`. Retained desired values therefore remain dormant until
the operator explicitly resumes them. Unknown integration payload schemas,
invalid desired state, malformed fields, and corrupt inheritance graphs fail
setup closed. Future migrations must be explicit before accepting a new schema.

## Compatibility and privacy

Entry and Store migrations are explicit and idempotent. Unknown future schema
versions fail closed. Diagnostics redact host, port, unit ID, serial, profile
settings, desired values, and raw error text that could contain endpoints.

Config-entry and device diagnostics contain only component/client versions,
non-sensitive policy, connection/scheduler health, connection generation, tier
success/freshness, and availability/error counts plus canonical register keys.
They never serialize config-entry data, device identifiers, controller values,
raw words, desired/profile documents, timestamps, or exception text; known
sensitive field names receive a second redaction pass.

Persistent repairs use opaque hashes rather than entry IDs. They exist only for
live identity mismatch, invalid Store content, or unsupported Store schema and
are removed after verified recovery. Transient disconnection never creates a
repair. Store/setup errors and public communication exceptions discard raw
external exception chains before Home Assistant can log them.

Public release requirements remain blocked until an exact client artifact is
published with approved ownership and license metadata.
