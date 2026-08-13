# TASK-014: Implement Authority Modes And Safe Control Entities

## Status

- Status: done
- Milestone: M05
- Dependencies: TASK-005, TASK-011–013
- Blocks: TASK-015–018

## Expected Current State

All values are observable, but no native number/select/switch control or common
mutation owner enforces monitor/temporary/persistent behavior.

## Source Details This Task Must Preserve

- Entity state is confirmed device state, never requested state.
- Monitor rejects before persistence/I/O; temporary uses `persist=False`;
  persistent restorable settings use `persist=True`.
- Non-restorable safe fields never become desired ownership.
- All operations serialize behind the entry lock and use fresh relational
  preflight.

## Implementation Contracts And Gaps

- Runtime mutation API rechecks mode, stopping, identity, availability, and
  validation after acquiring the lock.
- Public catalogue/controller APIs perform normalization and verified writes.
- `ServiceValidationError` represents caller misuse; `HomeAssistantError`
  represents communication/verification/persistence/runtime failure with
  translated messages.
- Partial/queued outcomes remain inspectable without volatile entity attributes.

## Implementation Plan

1. Write a mode-by-platform matrix for safe numbers, selects, switches, unknown
   enum state, non-restorable settings, offline/verification failures, and
   unload/mode-change races.
2. Add concurrency tests using a blocking external fake; prove no poll, second
   write, or other same-entry operation interleaves.
3. Implement the runtime mutation owner and translated typed-error mapping.
4. Implement safe number/select/switch entities from the overlay; entities
   delegate and never update state optimistically.
5. Run context-aware peer preflight under the outer lock.
6. Publish verified cache/snapshot results after success or partial failure
   without redundant unconditional read-back.
7. Expose bounded pending/queued summary status separately if approved.
8. Update control/action contracts and operator mode documentation.

## Expected Deliverables

- Native safe control entities.
- Three-mode mutation enforcement and translated errors.
- Confirmed-state and compound-operation behavior.

## Acceptance Criteria

- Monitor mode generates zero Store mutations and zero Modbus writes.
- Temporary failure leaves storage unchanged.
- Persistent failure may remain durably queued and explicitly says so.
- Entity state never becomes requested before verified read-back.
- Unknown enum values cannot become writable select options.
- Same-entry operations serialize; another entry remains responsive.

## Validation

- Full authority/platform/error/concurrency matrix through HA entity actions.
- Repository mutation and Modbus request counts on all unhappy paths.
- Relational stale/unavailable peer tests, partial response tests, full
  regression, LOC/docstring checks.

## Edge Cases And Risks

- Monitor-mode controls remain visually actionable to preserve stable domains;
  translated rejection and visible mode status are required.
- Persistent commit can succeed before I/O fails; error wording must preserve
  both facts.
- External writers remain outside the local operation lock.

## Completion Evidence

- All reviewed controls register: 39 number, 20 select, and 10 switch entities;
  guarded action registers remain absent.
- Mode tests prove monitor produces zero Store revisions and zero writes,
  temporary number/select/switch operations leave desired empty, and persistent
  operations durably own the verified setting.
- The one runtime mutation boundary performs all lifecycle/authority/identity
  checks under the entry operation lock and delegates fresh relation preflight
  and verified writes to the public client.
- Errors use translated HA service/runtime exception types; entity state is
  republished only after client completion.
- Follow-up completion audit directly proves stopping/unavailable/disconnected
  races, identity drift, dormant ownership, fresh relational rejection,
  transport retry exhaustion, and write-readback mismatch. Persistent failure
  keeps desired intent active and queued while HA state remains confirmed.
- Follow-up focused control validation: `12 passed`; full Home Assistant:
  `74 passed`; full standalone regression: `172 passed, 2 skipped`.

## Stop Conditions

- Context-aware validation cannot be performed under one operation boundary.
- HA entity state must be updated optimistically to function.
- A mapped control is dangerous or lacks approved validation semantics.
