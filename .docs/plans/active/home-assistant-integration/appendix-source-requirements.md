# Appendix: Source Requirements Ledger

## Original Request Digest

The device controller must become usable directly in Home Assistant. Individual
controls, settings, and datapoints should appear as native capabilities. Values
must refresh automatically so appropriate measurements can be plotted as time
series. Users should select a profile to change multiple settings together and,
ideally, save the current persistent configuration as a new profile similarly
to the existing TUI.

Clarified user choices:

1. HACS/manual native custom integration first.
2. Per-device `monitor_only`, `temporary`, and `persistent` modes.
3. Exact TUI profile-capture behavior initially.
4. Home Assistant-owned profile storage.
5. All supported datapoints deliberately classified, curated defaults, and no
   ordinary dangerous communication/reset controls.
6. Multiple devices from the start and configurable polling in seconds.

## Current Behavior

### Controller and transport

- `WolfCWL2` is an async public facade over a Waveshare TCP-to-Modbus gateway.
- It exposes start/stop, tier polling, refresh, snapshot, subscriptions, typed
  writes, desired state, reconciliation, profile preview/apply/capture, and
  one-shot actions.
- Three poll tiers and one reconcile loop can be controller-owned; start also
  performs an all-tier initial poll.
- Transport retries/reconnects and serializes individual Modbus requests.
- The request lock does not make a multi-block poll or multi-register operation
  indivisible.
- Transport loss can leave unvisited cached values individually marked
  available even when the controller is disconnected.

### Catalogue and data

- 154 logical values are defined in one canonical JSON catalogue: 44 fast, 90
  slow, 18 static, and 2 never-polled.
- 78 definitions are writable, 69 restorable, 40 optional, 4 dangerous, and 2
  one-shot.
- Metadata includes name, description, register table/address, codec, word
  count, scale, unit, enum, bounds, step, poll tier, and safety flags.
- Value state carries decoded value, raw data, unit, availability, timestamp,
  and error.
- The TUI's 19 overview keys provide evidence for an initial high-signal
  surface but do not settle the complete default-enabled list.

### Writes and desired ownership

- Submitted settings are normalized and cross-validated.
- Persistent desired state is committed before device I/O.
- Activation-sensitive writes are ordered last.
- Normal writes use read-back verification.
- Bulk/profile operations are sequential and report partial results; the device
  provides no transaction, rollback, revision, or compare-and-swap.
- A persistent offline/verification failure may leave desired ownership queued
  while current device state remains unchanged or unavailable.
- Existing relational validation does not reliably combine a temporary change
  with fresh confirmed peer values; this is a Home Assistant safety gap.

### Profiles and capture

- Profiles support safe names, descriptions, inheritance, ordered parents,
  merge/replace, `unset`, cycle and path rejection, restorable-setting
  validation, deterministic deltas, collision guards, and atomic file save.
- Persistent apply saves desired state and `last_profile` before sequential
  device writes.
- `last_profile` is capture lineage, not proof the live appliance matches.
- TUI capture reads only canonical persistent desired ownership and the exact
  lineage parent. It excludes temporary changes, telemetry, and unowned live
  values.
- Save rejects an empty delta or existing name without explicit overwrite.
- Save neither applies/selects the new profile nor changes desired/lineage.
- Current profile/file results and construction are filesystem-shaped.

### Configuration, UI, tests, and packaging

- `WolfCWL2` currently requires a schema-versioned JSON path. Connection,
  polling, desired, profile path, and state-output path live in that file.
- Some JSON/profile filesystem operations run synchronously in async methods.
- The CLI and Textual TUI use file-backed behavior.
- Textual is currently a mandatory package dependency.
- Tests replace the external gateway while exercising real catalogue, codec,
  validation, persistence, profile, controller, transport, CLI, and TUI logic.
- Physical tests are opt-in and read-only.
- No Home Assistant integration or distribution metadata currently exists.

## Target Behavior

### Installation and configuration

- A manual/HACS custom integration installs under one immutable domain.
- A UI config flow probes the endpoint read-only, verifies supported appliance
  identity, uses the stable serial as unique ID, and prevents duplicates.
- Multiple entries remain fully isolated even when they share a gateway.
- A reconfigure flow changes endpoint fields only after verifying the same
  serial and updates the existing entry.
- An options flow selects authority and fast/slow/static/reconcile intervals in
  seconds, with one reload mechanism.

### Lifecycle and polling

- Each entry owns one client, coordinator/scheduler, Store, outer operation
  lock, expected identity, authority, deadlines, and status records.
- The client initializes without initial polling, restoration, background
  tasks, or state-file output.
- The coordinator performs the only initial poll and only periodic schedule.
- Persistent restore occurs only after live identity verification.
- Tier deadlines are monotonic, all enabled intervals meet the supported lower
  bound, and missed cycles do not catch up in a burst.
- Polling/reconciliation remains active when every entity is disabled.
- Entity availability combines latest coordinator success, controller
  connection, per-value availability, and tier freshness.

### Entities and time series

- Every catalogue key has exactly one entity/composite/diagnostic/action-only
  disposition in a validated HA-only overlay.
- Wire facts remain in `register_catalogue.json`; HA platform, device/state
  class, category, precision, translation, and default enablement live in the
  overlay.
- Stable IDs use serial plus canonical key/semantic suffix.
- A curated set begins enabled; optional, installer, static, identity, and
  diagnostic capabilities generally begin disabled.
- Entities read coordinator memory and do no I/O from properties.
- Appropriate present-time numeric values use `MEASUREMENT`. Counter totals
  remain unclassified until reset/monotonic behavior is proven.
- Recorder is the only time-series owner; no duplicate client state history is
  written.
- Raw words, volatile timestamps, exceptions, desired maps, and profile bodies
  stay out of ordinary state attributes.

### Authority modes and controls

#### Monitor-only

- Poll and record.
- Show stable setting state where the entity domain is retained.
- Reject every mutation, apply, capture save, reconcile, release, and reset
  before persistence or device I/O.

#### Temporary

- Poll and record.
- Safe writes/profile settings use `persist=False`.
- Desired and lineage remain unchanged and inactive.
- No startup/reconnect/periodic reconcile.
- Capture save is rejected by the safe v1 default unless explicitly changed by
  DEC-003; temporary writes are never captured.

#### Persistent

- Safe restorable writes use `persist=True`; non-restorable safe writes remain
  temporary.
- Desired state is committed before I/O.
- Verified startup/reconnect and periodic reconciliation enforce ownership.
- Capture uses active persistent desired ownership.

#### Shared write rules

- All high-level operations take one outer lock per entry.
- Candidate state is validated against fresh confirmed relational peers.
- Entities never optimistically show a requested value.
- Typed validation misuse maps to translated validation errors; communication,
  verification, persistence, and partial failures map to truthful runtime
  errors.
- A persistent failure explicitly reports queued ownership while confirmed
  state remains actual/unknown.
- Changing away from persistent retains dormant state but stops enforcement.
- Returning to persistent requires explicit resume/apply or clear ownership.

### Profiles and capture

- One versioned per-entry Store owns revision, desired, lineage, profile
  documents, and last successful HA profile application.
- Store schema version and portable profile schema version are distinct.
- Persistent apply validates the complete candidate, atomically saves desired
  plus lineage, then writes sequentially.
- Temporary apply writes resolved settings only; `replace` and `unset` are not
  live clearing operations.
- The profile selector is a command surface whose state is last fully
  successful HA application, not lineage or live match.
- Capture preview returns a revision and exact delta.
- Save may reject stale expected revisions, validates the complete descendant
  graph on overwrite, and refreshes options without entry reload.
- HA storage is not watched/shared with CLI/TUI. Import/export and cross-device
  sync are v1 non-goals, while the schema remains portable for later work.

### Dangerous and one-shot operations

- Modbus interface, address, and speed remain read-only diagnostics.
- No generic register write service exists.
- Filter reset is action-only in v1, control-mode gated, and requires exact
  `EXECUTE ACTION`.
- Appliance reset has no entity and requires per-entry opt-in, one target,
  control-enabled mode, exact `RESET APPLIANCE`, expected serial, live serial
  match, and HA permission.
- Accepted appliance reset reports command dispatch only, marks the runtime
  unavailable, and lets normal reconnect behavior proceed.
- Confirmation strings reduce accidents and are not proof of human presence.

### Diagnostics, migrations, and release

- Diagnostics contain versions, non-sensitive options, scheduler/task health,
  connection generation, tier success/freshness, and categorized availability
  information.
- Endpoint, serial, entry identity, profile text, live/desired data, raw words,
  and raw exceptions are excluded/redacted; client logs are sanitized.
- Repairs address only actionable identity/schema/storage faults.
- Config-entry and Store versions exist from release one; later changes include
  tested migrations.
- A lightweight published client is pinned exactly by the component manifest.
- HACS/manual packaging contains all runtime integration files under its
  component directory and complete English translations.

## User Interaction Requirements

- Configuration occurs through Home Assistant UI flows, not a JSON path.
- Options clearly explain authority and persistent external-writer override.
- Returning to persistent with dormant desired values shows exact pending keys
  and asks for an explicit disposition.
- Control failures explain validation versus communication versus verification,
  and whether desired state remains queued.
- Advanced capabilities remain enableable in the entity registry.
- Profile options update immediately after capture; saving does not imply
  applying or matching.
- Dangerous actions require server-side confirmation inputs on every call.
- Documentation explains polling load, Recorder behavior, profile lineage,
  partial application, unavailable data, and recovery/removal.

## Architecture And Ownership Boundaries

```text
Home Assistant custom integration
  config/reconfigure/options flows
  per-entry runtime + coordinator + operation lock
  HA Store adapter + entities + actions + diagnostics/repairs
                     |
                     v
public wolf_325 client facade
  transport + canonical catalogue + codecs + validation
  verified writes + desired/profile semantics
                     |
                     v
PyModbus and physical gateway/appliance
```

- Dependency direction is one-way downward.
- CLI/TUI keep file adapters; HA implements host-owned repositories.
- One HA entry owns one appliance/unit and mutable state is never shared across
  entries.
- Recorder owns time series; HA Store owns desired/profile state; the client
  owns device/protocol semantics.

## Performance Requirements

- Minimum configured interval is never below the supported Home Assistant floor
  and final bounds are measured against the gateway.
- One tiered coordinator batches due work; no independent entity polls.
- No missed-cycle burst after outage.
- Unchanged comparable coordinator data suppresses needless dispatch.
- Volatile attributes and forced Recorder updates are forbidden.
- Blocking filesystem and serialization work must not stall the HA event loop.
- Broad disabled entity coverage does not imply skipped register blocks; the UI
  and docs must not promise false traffic reduction.

## Implementation-Critical Details

- `desired + last_profile` is one durable transaction before persistent I/O.
- Outer lock order is HA operation lock before internal controller I/O lock.
- Exactly one initial all-tier poll is allowed during setup.
- Restore gate is a matching live serial and supported appliance identity.
- Persistent failures can be durable even when device writes fail.
- Profile application is sequential; partial success remains applied.
- `last_profile`, last successful HA apply, and live match are distinct.
- Capture never performs Modbus I/O.
- Unknown future read enum values remain observable; writable selects offer only
  documented options.
- Packed device date/time values are not exposed as misleading independent
  numbers while their composite contract is unresolved.

## Rejected Approaches And Rationale

- **Controller file config under HA storage:** duplicates configuration,
  preserves blocking I/O, and weakens future Core compatibility.
- **Controller background loops plus coordinator:** creates two owners and
  makes unload/availability/concurrency unprovable.
- **Vendored client copy:** creates divergent release streams and duplicated
  protocol behavior.
- **Optimistic controls:** misrepresent normalization, verification, offline
  queues, and partial failures.
- **All entities enabled:** creates an unusable interface and Recorder churn.
- **Schema-driven UI without semantic overlay:** codecs cannot determine
  Home Assistant meaning or safe defaults.
- **Live profile match inferred by select:** external changes and partial
  profiles make the claim untruthful.
- **Shared profile directory:** cross-process stale reads and last-writer races.
- **Generic dangerous writes:** communication changes can sever the connection
  and invalidate entry configuration without a recovery transaction.

## Rationale

The design optimizes truthfulness and recoverability over apparent immediacy.
It retains the mature device semantics already tested in the client, isolates
Home Assistant lifecycle and storage conventions in an adapter, exposes broad
capability without overwhelming default users, and makes persistent authority
an explicit operator choice.

## Traceability

| Requirement area | Primary tasks |
|---|---|
| Immutable product/release decisions | TASK-001 |
| Test and architecture baseline | TASK-002 |
| Store-neutral desired/profile semantics | TASK-003, TASK-010 |
| Direct lifecycle construction | TASK-004, TASK-011 |
| Relational validation | TASK-005, TASK-014 |
| Event-loop/log/package safety | TASK-006–007 |
| HACS component/configuration | TASK-008–009 |
| Multi-device polling/availability | TASK-011 |
| Complete datapoints/defaults | TASK-012–013 |
| Authority/confirmed controls | TASK-014–015 |
| Profile selection/application | TASK-016 |
| Profile capture | TASK-017 |
| Guarded resets | TASK-018 |
| Diagnostics/repairs/migrations/privacy | TASK-019 |
| Documentation/distribution/physical validation | TASK-020 |
