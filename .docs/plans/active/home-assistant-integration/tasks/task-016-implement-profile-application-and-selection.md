# TASK-016: Implement Profile Application And Selection

## Status

- Status: done
- Milestone: M05
- Dependencies: TASK-003, TASK-010, TASK-014–015
- Blocks: TASK-017, TASK-019

## Expected Current State

Safe individual controls and persistent ownership work, and HA Store contains
profiles, but users cannot select/apply them through Home Assistant.

## Source Details This Task Must Preserve

- Profile apply is validated, ordered, sequential, and partially fallible.
- Temporary apply writes resolved settings without ownership mutation;
  `replace`/`unset` do not clear live values.
- Persistent apply atomically saves full desired plus lineage before I/O.
- `last_profile`, last successful HA apply, and live match remain distinct.

## Implementation Contracts And Gaps

- Synthetic profile select options come from the per-entry Store and refresh
  dynamically.
- Select state means last fully successful HA application only; temporary state
  is runtime-only after restart unless an approved contract says otherwise.
- Profile apply action may return detailed success/failure/not-attempted results.
- Partial failure never advances last-successful state and never claims rollback.

## Implementation Plan

1. Write tests for dynamic options, monitor rejection, temporary/persistent
   apply, replace/unset differences, order, partial failure, pending desired,
   restart, external drift, and last-successful/lineage separation.
2. Implement a profile runtime service using the public profile engine and
   entry operation lock.
3. Preflight complete resolved settings and relational peers before Store/I/O.
4. Implement persistent atomic desired/lineage commit then sequential writes;
   implement temporary settings-only writes.
5. Add the synthetic select and optional response action with translated typed
   errors.
6. Publish verified partial results and profile status without claiming live
   match.
7. Update profile application/entity/action workflows and docs.

## Expected Deliverables

- Native profile selector and detailed apply action.
- Correct temporary/persistent semantics and partial status.
- Separate lineage and last-successful facts.

## Acceptance Criteria

- Monitor apply performs no mutation.
- Temporary apply changes no desired/lineage Store data.
- Persistent desired/lineage commits before first write.
- Partial success remains applied and truthfully reported; no rollback claim.
- Select advances only after all target read-backs succeed.
- External drift does not cause a false live-match claim.

## Validation

- HA select/action/state/Store/request-order tests and blocked-gateway
  serialization tests.
- Profile graph/inheritance/replace/unset regression and two-entry isolation.
- Full suite and docs checks.

## Edge Cases And Risks

- Multiple partial profiles can match by coincidence; do not infer selection.
- Persistent partial apply leaves intended ownership ahead of device state.
- A profile may become invalid after an overwritten parent; TASK-017 guards
  graph mutation while apply must still validate at execution.

## Completion Evidence

- Stable `<serial>_profile` select exposes the per-entry Store catalogue and
  delegates resolution, replace/unset, ordering, validation, and verification
  to the public client engine.
- Tests prove monitor rejection without mutation, temporary runtime-only
  success, persistent desired/lineage commit, and a distinct last-full-success
  marker/state.
- Key-only logging and translated errors preserve partial-failure truth without
  values or endpoints; persistent partial intent remains queued and the selector
  does not advance.
- Follow-up completion audit injects external failure after one successful
  profile write and proves the full desired/lineage transaction remains queued,
  the applied write is not rolled back, and neither Store nor runtime success
  markers advance.
- Follow-up focused profile validation: `5 passed`; full Home Assistant:
  `74 passed`; full standalone regression: `172 passed, 2 skipped`.

## Stop Conditions

- Apply would require device-atomic rollback.
- Select state cannot be kept separate from lineage/live match.
- Profile resolution differs from CLI/TUI engine.
