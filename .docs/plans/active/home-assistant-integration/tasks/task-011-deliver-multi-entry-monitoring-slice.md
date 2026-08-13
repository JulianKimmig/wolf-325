# TASK-011: Deliver Multi-Entry Monitoring Vertical Slice

## Status

- Status: done
- Milestone: M03
- Dependencies: TASK-004, TASK-009, TASK-010
- Blocks: TASK-012–019

## Expected Current State

Entries and Stores can be created, but no controller runtime/coordinator owns
device setup, tier scheduling, availability, publication, reload, or unload.

## Source Details This Task Must Preserve

- One runtime/controller/coordinator/scheduler/outer lock per entry.
- Exactly one initial all-tier poll and no controller background tasks.
- Identity verification before persistent restore.
- Multiple entries remain isolated and polling survives disabled entities.

## Implementation Contracts And Gaps

- Typed runtime data includes controller, coordinator, Store adapters, operation
  lock, stopping flag, expected serial, authority, deadlines, and status.
- Coordinator ticks at the minimum enabled interval, uses monotonic due
  deadlines, skips missed bursts, and calls one `poll_once(tiers=due)`.
- Entry-lifetime listener/equivalent keeps scheduling alive without entity
  listeners.
- Availability combines refresh success, connection, per-value availability,
  and tier freshness.
- Setup/retry/unload/remove order is explicit and cleanup-safe.

## Implementation Plan

1. Write lifecycle/coordinator/multi-entry tests first, including exact request
   counts, fake monotonic time, all entities disabled, outages, optional
   failures, blocked operations, setup failure, reload, unload, and removal.
2. Implement typed runtime and one outer operation lock.
3. Construct/start the client without poll/restore/background/state output.
4. Run coordinator first refresh under the lock; verify supported identity and
   exact serial before forwarding platforms or persistent restore.
5. Implement tier/reconcile deadline scheduling and comparable immutable data
   with `always_update=False` where supported.
6. Add a minimal read entity to prove end-to-end publication and Recorder-safe
   behavior without broad metadata work.
7. Implement stopping/drain/cancel/stop/unload/remove order and independent
   entry cleanup.
8. Update lifecycle, operation, availability, and multi-device contracts.

## Expected Deliverables

- Runnable multi-entry monitoring component.
- Sole coordinator/scheduler and whole-operation lock.
- Stable minimal entity, availability, recovery, and cleanup.

## Acceptance Criteria

- Exactly one setup poll; zero client background tasks.
- Two entries poll/unload independently and one offline device does not block
  the other.
- All-entity-disabled entries continue scheduled work.
- Transport loss invalidates old values; optional failure remains local.
- Slow/static freshness is not hidden by fast success.
- Setup never restores before matching live identity.

## Validation

- HA lifecycle/multi-entry/coordinator tests with fake time and blocking gateway.
- Task/transport leak assertions across setup retry, reload, unload, remove,
  restart, and failed identity.
- Full client/component regression, LOC/docstring, `git diff --check`.

## Edge Cases And Risks

- Coordinator listener removal can stop scheduling unexpectedly.
- Unload during profile-like compound work needs bounded drain semantics even
  before profiles exist.
- Global coordinator failure must not erase localized optional errors.

## Completion Evidence

One typed runtime owns the controller, `EntryStore`, operation lock,
coordinator, authority, stopping state, and retained scheduler callback. Setup
runs one all-tier coordinator poll with zero client background tasks and verifies
the expected serial before forwarding the actual-supply-airflow sensor.
Deterministic tests prove due-tier batching, no early reads or catch-up bursts,
two-interval freshness, outage/unavailability and reconnect, scheduling with
all entities disabled, setup retry, two-entry isolation, and targeted unload.
Commit hash is recorded after this closed slice.

## Stop Conditions

- Serial identity fails DEC-006 evidence.
- Single-owner scheduling cannot remain active without adding a second poller.
- Safe unload requires cancelling a compound operation mid-write and claiming
  success.
