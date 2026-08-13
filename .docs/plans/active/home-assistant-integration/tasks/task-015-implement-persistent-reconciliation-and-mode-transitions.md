# TASK-015: Implement Persistent Reconciliation And Mode Transitions

## Status

- Status: done
- Milestone: M05
- Dependencies: TASK-010–011, TASK-014
- Blocks: TASK-016–017, TASK-019

## Expected Current State

Persistent writes create desired ownership, but the HA scheduler does not yet
restore/reconcile it or manage dormant ownership when modes change.

## Source Details This Task Must Preserve

- Restore only after a matching live serial.
- Temporary/monitor modes never enforce desired state.
- Leaving persistent retains dormant desired/lineage; returning must not
  silently reassert it.
- Ownership release removes desired keys without writing replacement values.

## Implementation Contracts And Gaps

- Coordinator owns due periodic reconciliation and reconnect-generation force
  apply under the same operation lock.
- Mode transition state machine includes inactive/dormant, resume/apply,
  clear/release, pending, synced, drifted, error/suspended if DEC-007 approves.
- Retry/backoff/suspension and repair thresholds follow DEC-007; no infinite
  tight write loop or invented policy.
- Desired status exposes bounded counts/categories, not full maps in Recorder.

## Implementation Plan

1. Write tests for startup/reconnect identity gate, periodic due work, external
   drift, persistence failure, repeated verification mismatch, mode transitions,
   dormant state, explicit resume/clear, release, and all-entity-disabled
   scheduling.
2. Implement one-shot reconcile using public client operations and coordinator
   deadlines, never a second loop.
3. Track connection generation and force reconcile only after identity remains
   verified.
4. Implement explicit persistent-exit and re-entry workflow from approved
   options/action UX.
5. Implement ownership release without live write.
6. Add bounded desired-sync status and approved retry/backoff/suspension logic.
7. Translate partial/pending outcomes and add actionable repair only if the
   approved threshold is reached.
8. Update authority/reconciliation/storage/operator contracts.

## Expected Deliverables

- Safe HA-owned persistent reconciliation.
- Explicit dormant ownership transition and release workflows.
- Bounded desired sync observability.

## Acceptance Criteria

- No restore/reconcile in monitor or temporary mode.
- No restore before verified serial, including reconnect endpoint changes.
- Returning to persistent never silently applies dormant values.
- Reconciliation shares the sole scheduler/lock and survives disabled entities.
- Retry behavior matches DEC-007 and cannot churn tightly forever.

## Validation

- Fake-time/connection-generation/mode matrix tests and blocked-gateway
  concurrency tests.
- Store-before-I/O and no-write release assertions.
- Repair/backoff tests if included; full regression.

## Edge Cases And Risks

- External local-panel drift can cause intentional repeated ownership writes.
- Clearing ownership must not imply resetting appliance values.
- Reload during transition can duplicate or lose the operator's explicit choice.

## Completion Evidence

- Store persists active/dormant authorization and the last loaded authority.
  Persistent exit deactivates retained ownership; re-entry with retained values
  stays dormant.
- Two explicit device buttons resume/force or clear-without-write. Persistent
  controls reject while retained ownership is dormant.
- Reconciliation is one coordinator deadline. It refreshes desired values,
  gates reconnect work on refreshed serial identity, skips missed bursts, and
  retries queued errors at the configured interval without an invented
  suspension threshold.
- Tests cover drift restoration, no silent mode-round-trip restore, explicit
  resume, and write-free clear. Full HA validation: `45 passed`.
- System-of-record contracts/workflow updated; commit recorded after this slice.

## Stop Conditions

- DEC-007 is unresolved when retry/suspension behavior is required.
- Re-entry UX cannot obtain an explicit dormant-state decision.
- Reconciliation needs a second independent scheduler.
