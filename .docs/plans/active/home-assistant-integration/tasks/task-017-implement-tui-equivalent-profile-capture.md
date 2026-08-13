# TASK-017: Implement TUI-Equivalent Profile Capture

## Status

- Status: done
- Milestone: M05
- Dependencies: TASK-003, TASK-010, TASK-016
- Blocks: TASK-019

## Expected Current State

HA profiles can be applied, but users cannot preview or save a new profile from
persistent desired ownership.

## Source Details This Task Must Preserve

- Capture source is durable `desired`, parent is exact `last_profile`.
- Temporary writes and live telemetry are excluded.
- Parented capture records changed/new settings and inherited removed keys as
  `unset`; standalone capture records full desired state.
- Save rejects unsafe/suffixed names, self/cycles/missing parents, empty delta,
  and collisions without overwrite.
- Save does not apply/select or alter desired/lineage.

## Implementation Contracts And Gaps

- DEC-003 controls whether temporary mode may save; safe default is persistent
  only. Monitor save is always rejected.
- Preview returns exact delta, base, replace, `has_changes`, and Store revision.
- Save accepts name, optional description, explicit `overwrite=false`, and
  optional expected revision.
- Overwrite validates the resulting complete graph including descendants in one
  transaction.
- Profile select options refresh without entry reload.

## Implementation Plan

1. Write exact parity tests using current TUI capture fixtures for parented,
   standalone, unset, empty, collision, overwrite, invalid name, cycles,
   descendant invalidation, temporary exclusion, and no Modbus I/O.
2. Add HA action tests for target resolution, permissions if approved, revision
   race, translated errors, response shapes, and mode gates.
3. Implement preview through the shared pure profile engine and Store snapshot.
4. Implement atomic save/overwrite with expected-revision and full-graph
   validation.
5. Refresh dynamic profile options after success without reload.
6. Confirm saved profile is not applied/selected and desired/lineage is
   unchanged.
7. Update HA storage/action/profile-capture workflow and user docs.

## Expected Deliverables

- Preview and capture actions with response data.
- Exact TUI semantic parity over HA Store.
- Revision/collision/overwrite safety and dynamic options.

## Acceptance Criteria

- Capture performs zero Modbus requests.
- Saved delta is byte/semantic equivalent to the shared engine result.
- Temporary changes never enter saved profiles.
- Collision/empty/stale revision/invalid graph cannot mutate the Store.
- Success changes one profile document only and refreshes options.

## Validation

- Shared profile parity suite, HA action/Store/restart tests, concurrent preview /
  save revision test, mode matrix, two-entry isolation, full regression.

## Edge Cases And Risks

- Temporary dormant desired capture is a product choice, not inferred TUI
  behavior.
- Overwriting a parent can invalidate descendants.
- Profile name is durable identity and must not be replaced by description.

## Completion Evidence

- Response-capable `preview_profile_capture` and `save_profile` actions target a
  loaded config entry and are described for the HA action editor.
- Capture is persistent-only and delegates exact parented/standalone settings,
  `unset`, replace, empty, collision, suffix/name, overwrite, and full-graph
  validation semantics to the shared client engine.
- Save supports an expected Store revision, updates dynamic selector options,
  and never advances selection or mutates desired/lineage.
- Tests prove exact derived delta, stale-revision rejection, temporary
  exclusion, and zero capture-time Modbus reads/writes. Focused validation:
  `2 passed`.
- System-of-record/action workflow updated; full suite and commit recorded after
  this slice.

## Stop Conditions

- DEC-003 is unresolved for temporary mode and implementation would choose it.
- HA Store cannot atomically validate and commit the full graph.
- Capture source would need live device reads.
