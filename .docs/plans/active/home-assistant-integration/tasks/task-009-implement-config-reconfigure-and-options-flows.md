# TASK-009: Implement Config, Reconfigure, And Options Flows

## Status

- Status: done
- Milestone: M03
- Dependencies: TASK-004, TASK-008
- Blocks: TASK-011, TASK-019

## Expected Current State

The component loads but cannot create a device entry. The public client can be
constructed directly and probed without implicit polling/restoration.

## Source Details This Task Must Preserve

- One config entry per appliance/unit and multiple entries from release one.
- Read-only setup probe; serial-backed stable unique ID; no host fallback.
- Endpoint reconfigure verifies the same serial.
- Options choose authority and second-based polling with one reload mechanism.

## Implementation Contracts And Gaps

- User data: host, port, device ID, transport, address offset, and approved
  connection settings.
- Options: authority, enabled tiers, fast/slow/static/reconcile seconds, and
  approved advanced timeout/retry controls.
- Intervals meet DEC-005 and never silently clamp invalid values.
- `OptionsFlowWithReload` or one update listener, not both.
- Probe opens no persistent Store mutation and performs no write/restore.

## Implementation Plan

1. Write config-flow tests for success, cannot-connect, unsupported identity,
   duplicate serial, two serials, invalid fields, and cleanup.
2. Write reconfigure tests proving same-serial update/reload and mismatch abort
   without creating a second entry.
3. Write options tests for all modes, tier toggles, boundary intervals, dormant
   desired warning inputs, and exactly one reload.
4. Implement a small client probe adapter using only public APIs.
5. Set unique ID from verified serial and store mutable endpoint facts in entry
   data, runtime policy in options.
6. Add full custom translation messages for forms/errors/aborts.
7. Update config-entry/action contracts and operator workflow.

## Expected Deliverables

- User, reconfigure, and options flows.
- Stable serial-based entries and duplicate prevention.
- Validated authority/polling policy storage.

## Acceptance Criteria

- Two distinct devices configure independently.
- Same endpoint/serial cannot create duplicates.
- Reconfigure refuses a different serial and updates only the current entry.
- Setup probe writes nothing and closes transport on every outcome.
- One options save causes exactly one targeted reload.

## Validation

- HA flow tests through public flow APIs, request/write counts, entry-count
  assertions, translation checks, and full component/client regression.
- Boundary tests at/below/above approved polling floor.

## Edge Cases And Risks

- Shared gateway with different unit IDs must not collide if serials differ.
- Serial may be unavailable on transient setup; report retry versus unsupported
  device correctly.
- Mode change UX must not silently activate dormant desired state.

## Completion Evidence

Connection schemas validate host, port, device ID, transport, and offset. The
real public controller performs a two-read, no-write, always-closed probe;
tests replace only the external PyModbus constructor. Serial identity drives
duplicate prevention and multi-entry creation. Reconfigure updates/reloads only
the same live serial and preserves data on mismatch. Options cover all three
authority modes, tier toggles, the 5-second boundary, invalid intervals, and
exactly one automatic reload. Custom English translations and the operator
workflow cover every implemented form/error/abort. Commit hash is recorded
after this closed slice.

## Stop Conditions

- DEC-001/005/006 is unresolved at implementation.
- Serial identity is missing/unstable/duplicated.
- Reconfigure cannot prove the same physical device.
