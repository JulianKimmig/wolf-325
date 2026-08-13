# TASK-018: Implement Guarded Reset Actions

## Status

- Status: done
- Milestone: M05
- Dependencies: TASK-011, TASK-014
- Blocks: TASK-019

## Expected Current State

Normal safe controls exist. Reset registers have no ordinary entity or action,
and communication settings remain read-only diagnostics.

## Source Details This Task Must Preserve

- Filter/appliance resets are never persistent desired state.
- Monitor mode rejects them.
- Filter reset uses exact `EXECUTE ACTION`.
- Appliance reset has per-entry opt-in, exact `RESET APPLIANCE`, expected/live
  serial verification, permission, one target, dispatch-only success,
  invalidation, and reconnect.
- Confirmation strings are accident guards, not proof of human presence.

## Implementation Contracts And Gaps

- DEC-009 decides whether appliance reset ships in v1; if deferred, retain tests
  proving no escape hatch.
- Register actions once at integration setup and resolve one loaded entry.
- Action handlers acquire the same operation lock and reject stopping/stale
  identity states.
- No automation-context heuristic substitutes for explicit gates.

## Implementation Plan

1. Write action tests for ambiguous/missing target, mode, option, phrase, serial,
   live mismatch, permission, unavailable device, unload race, and request count.
2. Add negative tests proving no writable communication entities or generic raw
   write action exists.
3. Implement filter reset action with exact phrase and control-mode guard.
4. If DEC-009 retains appliance reset, implement all server-side gates, call the
   public reset API, report dispatch only, invalidate runtime, and enter normal
   reconnect/backoff.
5. Ensure reset actions never mutate desired/profile Store state.
6. Add complete English translations/action descriptions and safety docs.

## Expected Deliverables

- Guarded filter reset and, if approved, appliance reset action.
- Negative dangerous-write surface guarantees.
- Reconnect and dispatch-only semantics.

## Acceptance Criteria

- Every failed gate produces zero reset writes and zero Store mutation.
- Accepted filter reset uses one verified public action path.
- Accepted appliance reset claims only dispatch, closes/invalidates stale
  connection, and recovers through normal lifecycle.
- Communication settings remain read-only and no raw escape hatch exists.

## Validation

- HA action/context/permission/target tests, request and Store counts, reconnect
  fake tests, translation/schema validation, full regression.
- No physical reset is part of automated or routine manual validation.

## Edge Cases And Risks

- Action context cannot prove human presence.
- Appliance reset may disconnect before a protocol response.
- Serial could be stale; require a current live identity gate.

## Completion Evidence

- DEC-009 outcome is implemented: both resets ship only as response-capable
  actions; neither has an entity or raw-register escape hatch.
- Filter gates exact target, control mode, `EXECUTE ACTION`, lifecycle, fresh
  serial, and public client dispatch. Appliance reset adds a disabled-by-default
  per-entry opt-in, `RESET APPLIANCE`, administrator context, and dispatch-only
  response.
- Tests prove every rejected gate writes nothing, accepted actions issue exactly
  one reset write, Store desired/profile state is unchanged, appliance cached
  availability is invalidated, and the normal coordinator path reconnects.
- Focused HA validation: `3 passed`; system-of-record contracts and operator
  workflow updated in the same slice.

## Stop Conditions

- Appliance reset inclusion is unapproved.
- Required HA permission semantics are unavailable in the selected HA version.
- Implementation needs a generic register write path.
- Any physical reset would be required without separate explicit authorization.
