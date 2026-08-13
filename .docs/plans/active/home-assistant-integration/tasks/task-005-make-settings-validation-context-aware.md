# TASK-005: Make Settings Validation Context-Aware

## Status

- Status: done
- Milestone: M02
- Dependencies: TASK-003, TASK-004
- Blocks: TASK-006, TASK-014

## Expected Current State

Cross-setting validation checks keys present in a mapping, and temporary writes
can be merged with persistent desired values rather than fresh live peers. A
single change can therefore create an invalid live relational combination.

## Source Details This Task Must Preserve

- Canonical bounds/enums/steps and existing cross-setting invariants.
- Validation failure changes neither persistent state nor device state.
- Multi-key activation ordering and partial-result semantics.

## Implementation Contracts And Gaps

- Define relational setting groups and required confirmed peer keys without
  duplicating register facts.
- For a touched group, compose the candidate from fresh confirmed peer values
  plus submitted changes.
- Reject unavailable/stale peers before persistence or I/O.
- Define coherent refresh/preflight and safe ordering for multi-key operations.
- Expose a public operation usable by HA without importing settings internals.

## Implementation Plan

1. Add tests reproducing invalid temporary airflow/PWM/CO2/analog/geothermal
   combinations, stale/unavailable peers, and safe multi-key updates.
2. Identify invariant groups from current validation code and catalogue keys.
3. Add a context-aware candidate builder that accepts confirmed state and a
   freshness contract.
4. Integrate preflight into public single/bulk temporary and persistent paths
   before any repository mutation.
5. Preserve safe write ordering and typed error details.
6. Document the fresh-peer and fail-closed public contract.

## Expected Deliverables

- Relational preflight API and tests.
- No persistent/device mutation after failed preflight.
- Public contract ready for control entities and profiles.

## Acceptance Criteria

- Invalid live combinations are rejected even when persistent desired differs.
- Valid multi-key changes pass and retain deterministic ordering.
- Missing/stale peer data fails clearly before storage or Modbus I/O.
- Existing controller validation behavior remains compatible.

## Validation

- Focused validation/controller tests with request and repository mutation
  assertions.
- Edge cases for partial group changes, enum/boolean peers, reconnect freshness,
  and scale tolerance.
- Full regression, docstring/LOC checks, `git diff --check`.

## Edge Cases And Risks

- Refreshing peers inside a compound operation can race without the future HA
  outer lock; define the client contract without pretending global exclusion.
- A stale threshold belongs to the host policy; avoid hard-coding HA timing into
  the client.
- Activation order may need group-specific dependencies.

## Completion Evidence

Implemented canonical relational groups and fresh confirmed-peer preflight
before desired mutation or device I/O. New tests first failed against stale
behavior, then proved invalid temporary/persistent candidates produce zero
writes and complete valid bundles avoid peer preflight reads; commit hash is
recorded after the closed slice is committed.

## Stop Conditions

- Safe preflight requires an appliance transaction the protocol cannot provide.
- Invariants cannot be represented without a material schema redesign.
- Behavior would persist or write before complete validation.
