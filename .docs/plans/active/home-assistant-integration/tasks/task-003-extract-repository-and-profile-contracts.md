# TASK-003: Extract Repository And Profile Contracts

## Status

- Status: done
- Milestone: M02
- Dependencies: TASK-001, TASK-002
- Blocks: TASK-004–006, TASK-010, TASK-016–017

## Expected Current State

`ConfigStore`, `ProfileLoader`, `SavedProfile.path`, and controller construction
remain filesystem-shaped. Profile semantics are mature and must not be copied
into the integration.

## Source Details This Task Must Preserve

- Atomic desired plus lineage persistence before persistent I/O.
- Existing names, inheritance, replace/unset, cycle/path safety, collision,
  overwrite, deterministic delta, and exact capture behavior.
- Existing file/CLI/TUI public behavior and examples.

## Implementation Contracts And Gaps

Create public async host-neutral contracts for:

- loading and atomically updating desired state plus `last_profile` with a
  revision;
- listing/loading/saving validated profile documents and validating a complete
  catalogue graph;
- store-neutral capture preview/save results with no mandatory `Path`;
- portable profile document/version models; and
- file-backed adapters preserving current API behavior.

Do not expose private controller modules to HA. Determine migration/compatibility
for existing `SavedProfile` callers before changing exports.

## Implementation Plan

1. Write repository contract tests first, including an in-memory test adapter
   and current file adapter.
2. Add equivalence tests for profile resolution, inheritance order, replace,
   unset, validation, cycles, names, collision, overwrite, capture delta, empty
   delta, lineage, and deterministic serialization.
3. Define typed public protocols/models with detailed docstrings.
4. Extract pure profile graph/resolution/capture logic from filesystem traversal.
5. Adapt `ConfigStore`/`ProfileLoader` behind the new contracts without changing
   CLI/TUI results.
6. Add atomic revision behavior needed for stale preview rejection and complete
   graph validation on overwrite.
7. Update public exports and controller/profile contracts conservatively.

## Expected Deliverables

- Host-neutral repository protocols and result/document models.
- Pure shared profile engine.
- Compatible file-backed adapters and public exports.
- Updated tests and system-of-record contracts.

## Acceptance Criteria

- File and in-memory backends produce identical behavior.
- Capture performs no device read and preserves exact TUI semantics.
- Store-neutral saves do not require a filesystem path.
- Existing CLI/TUI/profile tests pass unchanged unless an approved public
  expected behavior changed.

## Validation

- Focused repository/profile tests first, then existing profile/controller/CLI/
  TUI suites and full regression.
- Validate malformed/cyclic/missing-parent/descendant-overwrite cases.
- Check public import compatibility and all changed source files below 300 lines.

## Edge Cases And Risks

- Public `SavedProfile` compatibility may require an additional result type
  rather than mutation.
- Cross-setting validation of complete resolved profiles must remain canonical.
- Revision semantics must not weaken file atomicity.

## Completion Evidence

Implemented public `ProfileRepository`, store-neutral models/engine, filesystem
and memory repositories, full-candidate graph validation, optional saved path,
and shared example documents. File/memory parity and existing capture behavior
are covered by the 168-pass full suite recorded before the slice commit; commit
hash is recorded after the closed slice is committed.

## Stop Conditions

- A store-neutral API requires breaking existing public callers without an
  approved migration.
- Atomic desired/lineage persistence cannot be represented by the proposed
  protocol.
- Profile algorithms diverge between backends.
