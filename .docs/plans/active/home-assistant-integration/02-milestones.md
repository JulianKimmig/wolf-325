# Milestones

## Milestone Overview

| ID | Outcome | Tasks | Status |
|---|---|---|---|
| M01 | Approved contracts and executable baseline | TASK-001–002 | complete |
| M02 | Host-neutral, lightweight, released client | TASK-003–007 | in-progress |
| M03 | Native multi-device monitoring vertical slice | TASK-008–011 | complete |
| M04 | Complete reviewed entity and Recorder surface | TASK-012–013 | complete |
| M05 | Safe controls, persistence, profiles, and resets | TASK-014–018 | complete |
| M06 | Operationally hardened, documented HACS/manual release | TASK-019–020 | blocked externally after local qualification |

## M01 — Approved Contracts And Baseline

### Objective And Outcome

Replace unresolved immutable/product/release assumptions with durable decisions
and establish the Home Assistant test/documentation baseline before code
behavior changes.

### Related Tasks

- TASK-001
- TASK-002

### Entry Criteria

- Current repository and thought synthesis are available.
- User can provide or explicitly defer external ownership/release facts.

### Exit Criteria

- All TASK-001 decisions are approved, explicitly deferred, or marked as
  blockers with dependent tasks named.
- Architecture/contract decision records describe one client boundary, one
  per-entry owner, HA Store ownership, entity identity, and dangerous-operation
  exclusions.
- Exact HA test dependency/version and validation commands are discovered and
  baseline tests pass before implementation.

### Deliverables

- Durable decisions and TODO ownership.
- HA test/dev dependency strategy.
- System-of-record skeleton for the new domain/contracts/workflows.

### Validation Gates

- No immutable value is invented.
- Existing `uv` test suite passes.
- New test environment imports Home Assistant and the unchanged client.

### Risks And Decision Points

- Missing license/repository/package authority may block release but not local
  architectural work.
- Unsupported Python/PyModbus combinations may alter M02 packaging.

## M02 — Host-Neutral Lightweight Client

### Objective And Outcome

Provide a published, Home Assistant-safe client API while retaining existing
JSON, CLI, TUI, and profile compatibility.

### Related Tasks

- TASK-003
- TASK-004
- TASK-005
- TASK-006
- TASK-007

### Entry Criteria

- M01 contracts governing API/storage/package behavior are approved.

### Exit Criteria

- Direct runtime construction and injected repositories are public and tested.
- File-backed behavior is unchanged and off the event loop.
- Initial polling/background/restore/state output are explicit.
- Relational settings are validated against fresh peers.
- Base installation excludes Textual and sanitized logs do not expose device
  endpoints.
- An exact client artifact is installable in the selected HA environment, or
  TASK-007 is explicitly blocked on external publishing authority.

### Deliverables

- Public persistence/runtime/profile seams.
- Lightweight wheel and package metadata.
- Updated controller/profile contracts and tests.

### Validation Gates

- Existing full test suite and new repository-equivalence tests pass.
- Clean base import does not import Textual.
- Wheel installation and PyModbus compatibility pass in a clean environment.

### Risks And Decision Points

- Store-neutral result types can create public compatibility pressure.
- Cross-setting preflight may require new coherent refresh operations.

## M03 — Multi-Device Monitoring Vertical Slice

### Objective And Outcome

Deliver a native custom integration that configures, polls, publishes,
recovers, reloads, unloads, and isolates multiple appliances without writes.

### Related Tasks

- TASK-008
- TASK-009
- TASK-010
- TASK-011

### Entry Criteria

- M02 client seams required by the integration are stable.
- Domain, minimum HA version, and serial identity contract are approved.

### Exit Criteria

- Component structure, manifest, HACS metadata, and `translations/en.json`
  validate in the selected HA environment.
- Config/reconfigure/options flows support distinct serial-backed entries.
- One Store/runtime/lock/coordinator exists per loaded entry.
- Exactly one first poll and one periodic owner exist.
- A minimal read entity is stable, graphable where appropriate, unavailable on
  disconnect, recoverable, and isolated across two entries.
- Scheduler remains active with all entities disabled.

### Deliverables

- Runnable custom component and test harness.
- Versioned HA Store foundation.
- Multi-entry monitoring lifecycle.

### Validation Gates

- Two-entry integration tests and task-leak checks pass.
- Duplicate/mismatched serial flows behave correctly.
- Setup retry, reload, unload, and removal clean up exactly their own entry.

### Risks And Decision Points

- Serial stability may fail physical evidence.
- HA coordinator listener semantics may require an explicitly retained listener
  or equivalent single scheduler.

## M04 — Complete Entity And Recorder Surface

### Objective And Outcome

Classify every supported datapoint and expose a stable, curated, Recorder-safe
read surface.

### Related Tasks

- TASK-012
- TASK-013

### Entry Criteria

- M03 lifecycle and availability are stable.
- Entity-review policy and date/time composite decision are approved.

### Exit Criteria

- All 154 keys have one validated disposition.
- Default-enabled entities are reviewed; advanced/optional/diagnostic values
  remain available through the registry.
- Units, device classes, state classes, precision, unknown enums, and stable IDs
  are behavior-tested.
- No raw/timestamp/error/desired/profile churn enters ordinary Recorder states.

### Deliverables

- Declarative HA semantic overlay and validator.
- Sensor/binary/diagnostic/composite read platforms.
- Recorder compatibility contract and tests.

### Validation Gates

- Exactly-once catalogue coverage passes.
- Unproven counters have no long-term-statistics class.
- Platform/unique-ID snapshots are reviewed.

### Risks And Decision Points

- Platform assignment becomes a compatibility contract requiring migrations.
- Curated default entities do not necessarily reduce device polling traffic.

## M05 — Safe Control, Persistence, Profiles, And Resets

### Objective And Outcome

Add native controls and profile workflows without weakening confirmed-state,
persistence-before-I/O, partial-failure, identity, or dangerous-action safety.

### Related Tasks

- TASK-014
- TASK-015
- TASK-016
- TASK-017
- TASK-018

### Entry Criteria

- M04 entity identities and metadata are stable.
- Retry/mode-transition and temporary-capture decisions are approved.

### Exit Criteria

- All mutation paths obey the authority matrix and operation lock.
- Persistent restore/reconcile occurs only after live identity verification.
- Dormant desired ownership never reactivates silently.
- Profile apply/select and exact TUI capture preserve lineage and partial
  outcomes without claiming live match.
- Reset actions enforce all server-side gates and no raw/dangerous write escape
  hatch exists.

### Deliverables

- Number/select/switch controls.
- Desired sync/reconciliation and ownership release.
- Profile selector, apply, preview, and capture actions.
- Guarded filter/appliance reset actions.

### Validation Gates

- Full mode/operation matrix passes.
- Blocked fake gateway proves compound operations never interleave.
- Persistent failures remain queued without optimistic state.
- Profile and reset unhappy-path suites pass.

### Risks And Decision Points

- Persistent authority competes with external writers.
- Profiles are not device-atomic and cannot be rolled back truthfully.

## M06 — Operational And Release Readiness

### Objective And Outcome

Produce a diagnosable, private, migratable, documented, installable HACS/manual
release with read-only physical evidence.

### Related Tasks

- TASK-019
- TASK-020

### Entry Criteria

- M05 behavior is complete and the exact client artifact exists.

### Exit Criteria

- Diagnostics/logs redact sensitive device/profile/endpoint data.
- Repairs cover actionable identity/schema/storage faults only.
- Entry and Store version behavior and migrations are tested.
- HACS, manifest, translation, wheel, dependency, and disposable install checks
  pass.
- User docs cover setup, modes, polling, Recorder, entities, profiles, safety,
  recovery, and removal.
- Monitor-only physical validation confirms identity, cadence, availability,
  reconnect, and Recorder behavior without committed secrets.

### Deliverables

- Diagnostics, repairs, migration and privacy hardening.
- Complete operational/release documentation and validation evidence.
- Completed-plan handoff/move when all gates are genuinely satisfied.

### Validation Gates

- Clean manual and HACS custom-repository installations succeed.
- No task/transport leaks across restart/reload/unload/removal.
- No physical mutation occurs without a separately authorized workflow.

### Risks And Decision Points

- Current HACS/Home Assistant rules may change; reverify official sources.
- Public repository/package release access is external and can block
  publication; the current 2026.3+ custom-integration path uses a local brand
  asset.
