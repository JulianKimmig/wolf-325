# TASK-013: Implement Read Entities And Recorder Semantics

## Status

- Status: done
- Milestone: M04
- Dependencies: TASK-011, TASK-012
- Blocks: TASK-014, TASK-019

## Expected Current State

The overlay classifies every key and the coordinator publishes snapshots, but
only a minimal entity exists.

## Source Details This Task Must Preserve

- Stable serial/canonical-key unique IDs and translated device-relative names.
- Memory-only entity properties, no forced updates, no volatile attributes.
- Recorder and long-term statistics use legal reviewed semantics.
- Device disconnect versus localized optional failure is truthful.

## Implementation Contracts And Gaps

- Common coordinator entity owns device info, unique IDs, availability, and
  snapshot lookup.
- Read-only platforms cover sensor, binary sensor, read-only diagnostics, and
  approved composites.
- Unknown enums remain observable; enum sensor options/state-class rules are
  legal.
- Entity registry defaults apply only on first creation; documentation does not
  promise retroactive changes.

## Implementation Plan

1. Write platform/registry/state tests for representative and exhaustive overlay
   entries, unique IDs, device info, translations, defaults, availability, and
   Recorder metadata.
2. Implement common base entity and platform factories split by responsibility.
3. Map native values/units/classes/precision from overlay and canonical state.
4. Ensure raw/error/timestamp/desired/profile data is absent from ordinary
   attributes and `force_update` is false.
5. Implement unknown enum, optional unavailable, reconnect, and tier-stale
   behavior.
6. Implement approved date/time read/composite surface.
7. Test host/title/mode/interval/reload changes preserve IDs/history contract.
8. Update entity/Recorder documentation and user-facing enablement guidance.

## Expected Deliverables

- Complete read entity platforms and device registry information.
- Recorder-safe current/history behavior.
- Stable registry and translation coverage.

## Acceptance Criteria

- All entity-backed read dispositions instantiate correctly.
- Appropriate instantaneous telemetry is graphable; unproven totals are not.
- No volatile/high-cardinality attributes create Recorder churn.
- Disconnect makes all device values unavailable; optional failure affects only
  its entity.
- IDs remain stable across mutable entry changes.

## Validation

- HA public state/device/entity registry tests and Recorder metadata tests.
- Unknown enums, unit conversion legality, optional failures, staleness, restart,
  and two-entry collision tests.
- Full regression and source quality checks.

## Edge Cases And Risks

- Native HA unit conversion can change display while unique/statistics metadata
  must remain compatible.
- A static identity field may belong in device info rather than duplicate
  entities; overlay contract decides.
- Changing defaults does not update existing registries.

## Completion Evidence

- All 83 sensor dispositions register with `<serial>_<canonical key>` unique
  IDs and one serial-backed device; 23 are curated on by default.
- Common entity properties are cache-only, translated through a stable generic
  entity key, never force updates, and combine connection/tier/value
  availability.
- Recorder tests cover measurement metadata, graphable airflow, absent volatile
  attributes, unknown enum visibility, and disabled diagnostics producing no
  state.
- Full HA validation after implementation: `38 passed`.
- Durable entity contract and setup workflow updated; commit recorded after
  this closed slice.

## Stop Conditions

- HA rejects an approved unit/device/state-class combination.
- Stable platform assignment requires an unplanned migration.
- Date/time composite contract is still unresolved.
