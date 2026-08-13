# TASK-010: Implement Versioned Per-Entry Home Assistant Store

## Status

- Status: done
- Milestone: M03
- Dependencies: TASK-003, TASK-008
- Blocks: TASK-011, TASK-015–017, TASK-019

## Expected Current State

Public repository protocols exist, but the component has no HA-owned desired /
lineage/profile persistence or schema lifecycle.

## Source Details This Task Must Preserve

- One Store transaction owner per config entry.
- Desired plus `last_profile` commits atomically before persistent I/O.
- Profile documents preserve TUI semantics but are not live-shared with files.
- Removal deletes only the targeted entry's storage.

## Implementation Contracts And Gaps

Define one versioned JSON-safe payload with at least:

- Store schema version and revision;
- canonical desired mapping and optional `last_profile`;
- per-entry profile documents with portable schema versions; and
- last successful HA profile application where persistence is approved.

Use immediate awaited saves for safety-critical mutations, not delayed saves.
Define current/forward/corrupt schema behavior and migration hooks. Store
serialization behavior must be qualified for the selected HA version.

## Implementation Plan

1. Write HA Store adapter tests for empty initialization, round-trip, revision,
   atomic desired/lineage, profile graph, collision/overwrite, isolation,
   corruption, forward version, removal, and restart.
2. Define typed JSON-safe payload models and adapter interfaces over the one
   transaction owner.
3. Implement public desired/profile protocols using HA Store.
4. Seed approved canonical example profiles once without overwriting user data.
5. Implement schema load/migrate/reject behavior and per-entry storage keys.
6. Verify immediate save completes before repository calls return.
7. Update HA storage contract and profile workflow.

## Expected Deliverables

- Versioned per-entry Store and adapters.
- Atomic revisions and migration foundation.
- Storage isolation/removal behavior.

## Acceptance Criteria

- Desired/lineage is one durable revision.
- Profile resolution/capture matches file adapter behavior.
- Two entries never read/write/delete each other's records.
- Corrupt/unsupported storage does not open or write the appliance.
- Delayed save is not used for persistence-before-I/O.

## Validation

- HA Store public-surface tests, restart/removal/migration tests, equivalence
  tests from TASK-003, serialization/off-loop qualification, full regression.

## Edge Cases And Risks

- Store serialization threading differs by HA version.
- Separate repositories over one payload can accidentally make nontransactional
  writes; keep one mutation owner.
- Seed profiles must not overwrite user modifications on upgrade.

## Completion Evidence

`EntryStore` owns private key `wolf_cwl2.<entry_id>`, integration schema 1,
monotonic revisions, desired/lineage, last-successful profile truth, portable
documents, and one-time example seeding. Immediate `Store.async_save` is
followed by exact public-API readback before visible state changes. Tests cover
serialization, restart, customized seed preservation, isolation, targeted
removal, forward schema, corrupt graphs, missing markers, and a discarded
external write. No device source is mocked or opened. Commit hash is recorded
after this closed slice.

## Stop Conditions

- HA Store cannot provide awaited durability required before I/O.
- Payload cannot atomically represent desired plus lineage.
- Store migration needs user data loss or an unapproved fallback.
