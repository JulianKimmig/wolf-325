# Validation And Risk Plan

## Test Strategy

Every behavior change follows repository TDD:

1. Write failing behavior tests and edge cases before source changes.
2. Exercise real catalogue, codec, normalization, validation, controller,
   persistence, and profile logic.
3. Replace only external boundaries: Modbus gateway responses, Home Assistant
   host/runtime, filesystem timing, or package-index/install environment.
4. Implement until the focused tests pass.
5. Run affected regression suites, then the full `uv` suite at milestone gates.
6. Update owning `.docs` records and capture evidence in the task file before an
   atomic commit.

Tests must not assert source text or constants as a substitute for behavior.
Exact new commands are discovered and recorded in TASK-002; this plan does not
invent commands for dependencies that are not installed yet.

## Task Validation Rules

- Each task has focused success, failure, boundary, concurrency, cleanup, and
  migration/error tests appropriate to its outcome.
- Test names describe the contract, not the implementation mechanism.
- Async work uses deterministic clocks/events rather than prolonged sleeps.
- Compound-operation exclusion uses a blocking external fake, not mocked source
  methods.
- Entity tests go through config entries, registries, state machine, actions,
  and HA Store where practical.
- All new source modules and functions carry required detailed docstrings and
  remain below 300 lines.
- `git diff --check`, relevant tests, documentation cross-links, and clean
  status of the committed slice are recorded.

## Milestone Validation Rules

### M01

- All decision IDs have an approved/deferred/blocking state.
- Baseline existing tests pass before implementation changes.
- Selected HA test harness and validation commands run in the `uv` environment.

### M02

- File and injected repositories are behaviorally equivalent.
- CLI/TUI/controller regression suite passes.
- Initial polling can be suppressed without a hidden read.
- Relational preflight uses fresh peers and fails closed when peers are stale.
- Filesystem work is off-loop; state output can be disabled.
- Base wheel imports without Textual and installs in the selected HA
  environment.

### M03

- Two entries use independent serials, stores, clients, locks, schedules, and
  unload paths.
- Exactly one all-tier first poll and no controller background task occur.
- Polling/reconciliation owner remains live with all entities disabled.
- Setup retry, endpoint reconfigure, options reload, unload, remove, and restart
  leak no tasks or transports.
- Device disconnect invalidates old values; optional failures remain local.

### M04

- All 154 catalogue keys have one disposition and dangerous writes have no
  ordinary entity path.
- Stable IDs survive host/title/mode/interval/profile/reload changes.
- Unit/device-class/state-class combinations are legal and reviewed.
- Unproven counters have no long-term-statistics class.
- No volatile/high-cardinality state attributes or forced updates exist.

### M05

- Every mutation path is covered by the three-mode matrix.
- No poll/write/reconcile/profile/capture/reset interleaves inside one entry;
  another entry remains responsive.
- Confirmed state never becomes the requested value before read-back.
- Persistent failure remains queued and explicitly reported; temporary failure
  changes no storage.
- Restore/reconcile happens only after verified live serial.
- Profile tests cover inheritance, `replace`, `unset`, revisions, collisions,
  overwrite descendants, empty delta, lineage, partial failure, and option
  refresh.
- Reset tests cover option, mode, target, phrase, serial, permission,
  invalidation, and reconnect gates.

### M06

- Diagnostics and logs redact endpoint, serial, entry IDs, profile text, live
  values, desired maps, raw words, and endpoint-bearing errors.
- Repairs exist only for actionable identity/schema/storage faults.
- Entry and Store schema/version behavior and real migrations are tested.
- Wheel, exact manifest pin, translations, HACS metadata, clean manual/HACS
  installation, restart/reload/unload/removal, and docs checks pass.
- Read-only physical validation confirms identity, availability, cadence,
  reconnect, and Recorder behavior without committed secrets.

## Final Acceptance Checks

- The integration supports multiple independent config entries.
- Users can select monitor-only, temporary, or persistent authority per entry.
- All supported datapoints have a deliberate disposition; curated defaults are
  usable without hiding advanced capabilities.
- Appropriate values are graphable through ordinary Recorder semantics.
- Writes are validated, serialized, verified, and truthful on failure.
- Persistent desired ownership is committed before I/O and never restored to an
  unverified endpoint.
- Profiles apply sequentially with explicit partial outcomes and capture exactly
  the TUI desired/lineage source.
- Dangerous communication writes have no normal path; reset actions are
  server-side guarded.
- Installation uses an exact lightweight client artifact without Textual.
- User docs explain authority, polling, profiles, Recorder, entity defaults,
  safety, recovery, and removal.
- No physical mutation was run without separate authorization.

## Risk Register

| ID | Risk | Impact | Mitigation / gate |
|---|---|---|---|
| RISK-001 | Dormant persistent desired state is silently reactivated | appliance settings unexpectedly overridden | explicit resume/apply or clear-ownership transition; TASK-015 tests |
| RISK-002 | External panel/TUI/second HA instance writes concurrently | last-writer drift and repeated reconciliation | document authority, serialize only local work, expose bounded sync status |
| RISK-003 | Delayed or split Store saves violate persistence-before-I/O | queued ownership/lineage lost or inconsistent | one per-entry transaction owner and awaited save; TASK-010/014 tests |
| RISK-004 | Controller and coordinator both schedule work | duplicate load, race, task leaks | explicit no-initial-poll/background controls and exactly-one-owner tests |
| RISK-005 | Coordinator stops when entities are disabled | stale telemetry and stopped reconciliation | entry-lifetime listener/scheduler test in TASK-011 |
| RISK-006 | Partial profile application is presented as atomic | false operator confidence | no rollback claim; partial results and pending desired status |
| RISK-007 | Entity platform/unit/state-class changes fragment history | Recorder/statistics discontinuity | reviewed overlay, stable IDs, migrations/release notes |
| RISK-008 | Too-fast polling overloads gateway or HA | communication failure and database churn | minimum >=5 seconds, measured lower bound, no catch-up burst |
| RISK-009 | Disabled entities are assumed to reduce Modbus traffic | device load remains high | document block polling; expose tier toggles where safe |
| RISK-010 | Serial is not stable/unique | duplicate or wrong-device restore | physical gate; no host fallback; replan identity if disproven |
| RISK-011 | Cross-setting temporary write uses stale peers | invalid live device combination | fresh peer preflight and fail-closed semantics in TASK-005/014 |
| RISK-012 | Logs/diagnostics expose endpoint or device/profile data | privacy leak | sanitize client logs plus HA redaction and sentinel tests |
| RISK-013 | Published client pin is missing/incompatible | integration cannot install | TASK-007 clean-environment qualification before release |
| RISK-014 | HACS/HA APIs change during implementation | invalid packaging or obsolete APIs | recheck official docs at TASK-020 and when minimum HA version changes |
| RISK-015 | Confirmation strings are treated as security | unattended automation can reproduce them | option, permission, serial and target gates; document as accident prevention |
| RISK-016 | Monitor-only controls look actionable | confusing rejected calls | stable entities with translated rejection and visible authority diagnostics |
| RISK-017 | Source modules exceed repository LOC/docstring rules | unmaintainable implementation | modular responsibility split and per-task line-count review |

## Security, Privacy, And Data Checks

- No credentials currently exist, but treat future authentication fields as
  sensitive by contract.
- Redact host/IP, port, unit/entry identifiers, serial, profile names and
  descriptions, live values, desired mappings, raw words, and raw exception
  text from downloadable diagnostics.
- Sanitize connection logging before exceptions reach HA; redaction after log
  emission is impossible.
- Permission checks and unambiguous device targeting occur server-side for
  actions. UI schemas are not security boundaries.
- HA Store data remains per-entry and deletion removes only that entry.
- Export/import is a v1 non-goal, so no filesystem path or cross-device data is
  accepted through a hidden action.
- Never commit physical endpoint, serial, live state, Recorder export, or reset
  evidence containing secrets.

## Release And Handoff Checks

- Reverify official Home Assistant/HACS requirements against
  [research-notes.md](research-notes.md).
- Confirm package-index owner, Brands needs, supported versions, and exact
  release artifacts; public repository/license/URLs/code owner are resolved.
- Validate one integration directory under `custom_components`, complete
  `translations/en.json`, manifest keys, HACS metadata, and action descriptions.
- Install from a manual copy and HACS custom repository in a disposable HA
  instance.
- Exercise add, duplicate prevention, reconfigure, options, restart, reload,
  disable all entities, remove, and re-add.
- Record exact client/integration versions and validation evidence.
- Do not mark the plan complete while an external artifact or required check is
  absent; use `blocked` rather than redefining completion.
