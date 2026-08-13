# TASK-012: Classify The Complete Entity Surface

## Status

- Status: done
- Milestone: M04
- Dependencies: TASK-008, TASK-011
- Blocks: TASK-013–014

## Expected Current State

A minimal monitoring entity works, but no exhaustive HA semantic overlay exists
for 154 catalogue definitions and the default-enabled policy is not approved.

## Source Details This Task Must Preserve

- Catalogue remains the only wire/type/safety schema.
- Every supported key gets exactly one reviewed disposition.
- Defaults are curated; advanced values remain enableable.
- Communication settings are read-only diagnostics; reset registers are
  action-only; date/time needs an approved composite.

## Implementation Contracts And Gaps

The declarative HA-only overlay records:

- platform or explicit composite/diagnostic/action-only/no-entity disposition;
- translation key, device class, state class, native unit, precision;
- entity category and default enablement; and
- write/action policy where applicable.

It derives address, codec, range, step, enum, writability, restorable,
dangerous, optional, and poll tier from `RegisterDef`. DEC-004/008 must be
resolved before affected mappings are approved.

## Implementation Plan

1. Write validator tests for exactly-once 154-key coverage, real-key references,
   legal platforms/classes/units, dangerous exclusions, unknown enums, and
   curated defaults.
2. Inventory the catalogue by operator domain using existing TUI taxonomy and
   overview evidence.
3. Review each key for platform, Recorder meaning, category, precision,
   optional/static behavior, and default status.
4. Implement a declarative data file plus typed loader/validator; keep executable
   modules below 300 lines.
5. Record explicit composite/action-only choices for date/time and resets.
6. Snapshot/review the full mapping and default-enabled list.
7. Update the HA domain/entity/Recorder contract and code relationships.

## Expected Deliverables

- Complete HA semantic overlay and validator.
- Reviewed curated default set and disposition report.
- Durable mapping/compatibility contract.

## Acceptance Criteria

- Every catalogue key is classified exactly once.
- No wire metadata is duplicated in the HA overlay.
- Dangerous communication values cannot create writable entities.
- Unproven counters have no total state class.
- Date/time and reset dispositions match approved decisions.

## Validation

- Full catalogue coverage/metadata tests and reviewed snapshots.
- Legal unit/device/state-class validation against selected HA version.
- Diff review for defaults and platform assignment.

## Edge Cases And Risks

- Unknown firmware enum values must remain readable without becoming writable.
- Platform changes after release require registry migration/history review.
- All registry entities can still imply block polling even when disabled.

## Completion Evidence

- TDD coverage requires exact equality with all 154 canonical keys and validates
  platform, category, state-class, dangerous, reset, date/time, and default
  policies.
- Reviewed distribution: 83 sensor, 39 number, 20 select, 10 switch, and 2
  guarded action-only dispositions; 36 entities enabled for new entries.
- Communication settings are diagnostic sensors, clock fields are read-only,
  resets are action-only, and unproven counters have no state class.
- Durable contract: `.docs/contracts/home-assistant-entities.md`.
- Validation: `5 passed` in `test_entity_catalogue.py`; commit recorded after
  this closed slice.

## Stop Conditions

- DEC-004 or DEC-008 remains unresolved for required keys.
- A key cannot be safely mapped without new product scope.
- Overlay would need duplicated register addresses/codecs to function.
