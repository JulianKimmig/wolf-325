# TASK-019: Complete Diagnostics, Repairs, Migrations, And Privacy

## Status

- Status: done
- Milestone: M06
- Dependencies: TASK-009–018 as applicable
- Blocks: TASK-020

## Expected Current State

Functional monitoring/control/profile/reset behavior exists, but operational
diagnostics, actionable repairs, complete migration behavior, log/privacy
proof, and lifecycle hardening are incomplete.

## Source Details This Task Must Preserve

- Diagnostics help troubleshoot without endpoint, serial, profile, live/desired
  data, raw words, or raw exceptions.
- Repairs are for actionable identity/schema/storage faults, not transient
  disconnects.
- Config-entry and Store versions/migrations are explicit from release one.
- No task/transport leaks across setup/reload/unload/remove.

## Implementation Contracts And Gaps

- Diagnostic fields: component/client versions, non-sensitive mode/poll facts,
  task/coordinator health, connection generation, tier success/freshness, and
  categorized availability/error counts/keys.
- Redaction happens by construction plus HA redaction helpers; client logs are
  already sanitized by TASK-006.
- Repairs cover serial mismatch, corrupt/unmigratable Store, and unsupported
  schema only when user action can resolve them.
- Define entry `VERSION`/`MINOR_VERSION`, Store version behavior, forward-version
  rejection, and real migration functions only for actual schema changes.

## Implementation Plan

1. Write sentinel diagnostics/log tests containing host, port, serial, entry ID,
   profile name/description, desired/live values, raw words, and exception text.
2. Write repairs lifecycle tests for creation, persistence, ignore/resolve, and
   absence on transient outages.
3. Write config-entry/Store current, forward, corrupt, and real migration tests.
4. Implement config/device diagnostics with safe categories and second-layer
   redaction.
5. Implement only approved actionable repairs and resolution flows.
6. Harden setup/reload/unload/remove and operation-drain/task cancellation,
   including all entities disabled and one entry blocked while another lives.
7. Update privacy, diagnostics, repair, migration, and recovery records.

## Expected Deliverables

- Redacted diagnostics and sanitized operational logs.
- Actionable repair flows and schema/migration behavior.
- Leak-free lifecycle evidence.

## Acceptance Criteria

- No sentinel sensitive value appears in diagnostics or logs.
- Transient disconnect creates no persistent repair.
- Corrupt/forward storage fails safely before device mutation.
- Migrations are deterministic and tested; no fake migration exists.
- Reload/unload/remove leave no tasks/transports/listeners or foreign Store data.

## Validation

- Diagnostics snapshots, caplog sentinel tests, repairs tests, migration tests,
  task-leak/cancellation tests, two-entry blocking tests, full regression.

## Edge Cases And Risks

- Exception chaining can still log endpoint-bearing underlying errors.
- Over-redaction can remove useful categorized evidence.
- Unload during a compound operation must not report success after unsafe
  cancellation.

## Completion Evidence

- Migration sub-slice: config entry 1.1 migrates to 1.2 by adding only
  `allow_appliance_reset=false`; future entry schemas are rejected unchanged.
- Store wrapper/payload v1 migrates to v2 without desired/profile loss, advances
  revision once, and makes retained desired ownership dormant. Forward payloads
  remain fail-closed. Focused validation: `10 passed`; full HA: `57 passed`.
- Config-entry/device diagnostics expose versions, non-sensitive policy,
  scheduler/connection health, tier freshness, and categorized counts/keys.
  Host, port, serial, entry ID, profile name/description, desired/live values,
  raw words, and external exception text sentinels are absent from diagnostics
  and operational logs.
- Opaque persistent repair IDs cover identity mismatch, corrupt Store, and
  unsupported Store only. Tests prove dismissal, verified resolution, zero-I/O
  Store failure, and no repair for transient disconnection.
- Lifecycle tests prove unload drains an in-flight operation and leaves no
  controller task, listener, scheduler, or connected transport; a blocked entry
  does not delay another entry refresh.
- Client errors no longer chain raw gateway exceptions. Focused hardening:
  `11 passed`; full HA validation: `64 passed` before final regression.

## Stop Conditions

- Sensitive values cannot be removed without losing required function.
- Migration requires destructive data loss without user approval.
- Repair policy depends on unresolved retry thresholds from DEC-007.
