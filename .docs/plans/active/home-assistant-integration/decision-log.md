# Decision Log

## Accepted Decisions

### DEC-A01 — Distribution Direction

- Native custom integration for manual/HACS installation first.
- Preserve a credible future Home Assistant Core path.
- Do not build an add-on, bridge, or second protocol implementation.

### DEC-A02 — Authority Modes

- One mode per config entry: `monitor_only`, `temporary`, or `persistent`.
- Entity state is confirmed appliance state in every mode.
- Persistent desired state may be queued separately.

### DEC-A03 — Profile Capture Source

- Exact TUI capture semantics: durable `desired` delta relative to exact
  `last_profile` lineage.
- No live telemetry capture and no temporary-write capture.

### DEC-A04 — Profile Storage Ownership

- One versioned Home Assistant-owned Store per entry.
- No live shared profile directory or cross-process locking with CLI/TUI.

### DEC-A05 — Entity Surface

- Every supported catalogue key gets one reviewed disposition.
- Only a curated set is enabled by default.
- HA semantics live in a separate overlay; wire metadata stays canonical.

### DEC-A06 — Runtime Ownership

- One controller, coordinator/scheduler, Store, and whole-operation lock per
  entry.
- Home Assistant owns periodic polling and reconciliation.
- Controller background loops remain disabled.

### DEC-A07 — Dangerous Operations

- Communication settings remain read-only diagnostics in v1.
- Reset registers are action-only; appliance reset is strongly opt-in/gated.
- No raw-register escape hatch.

### DEC-A08 — Multiple Devices And Cadence

- Multiple config entries from release one.
- Polling intervals are user-configurable seconds with safe lower bounds.

### DEC-A09 — Profile Selector Truthfulness

- Selector state means last fully successful Home Assistant application.
- `last_profile` remains capture lineage.
- V1 does not claim current live profile match.

## Provisional Decisions Requiring TASK-001 Review

The local implementation decisions are now recorded in
[Decision 002](../../../decisions/002-home-assistant-product-contract.md):

- domain `wolf_cwl2`, initially scoped to the generation-1 CWL-2-325 catalogue;
- Home Assistant 2026.2.3/Python 3.13 as the tested host floor;
- no temporary-mode capture and no writable date/time surface;
- serial-only identity, five-second interval floor, and two-interval freshness;
- no unproven counter totals or invented reconciliation suspension threshold;
  and
- action-only guarded resets with no raw-register escape hatch.

Public ownership/release metadata and broader physical identity evidence remain
explicit external blockers, not provisional runtime behavior.

## Deferred Decisions And Features

- Core submission, discovery, TLS/authentication.
- Shared files, profile import/export, cross-device profile sync.
- Communication-setting reconfiguration wizard.
- Automatic live profile match.
- Total statistics for counters without physical evidence.
- Physical control/profile/reset test automation.
