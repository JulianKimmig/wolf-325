# Home Assistant Integration — Agent 4 Integrator Review

## Source Task

Produce an implementation-plan-ready architecture for a native Home Assistant
custom integration over the public `wolf_325` controller. The clarified scope
is HACS/manual installation first, multiple appliances, one lifecycle/poll
owner per appliance, stable full-but-curated entities, Recorder-safe history,
per-entry monitor-only/temporary/persistent control, Home Assistant-owned
profiles with the TUI's exact capture source and lineage semantics, guarded
dangerous operations, diagnostics, packaging, tests, and accurate
system-of-record records. This reasoning pass does not authorize implementation.

This review reconciles `perspectives.md`, `clarification.md`, and the reports
from agents 1–3 against the current source, tests, and `.docs` records.

## Chain-of-Thought Summary

- The three reports converge on the correct high-level shape: a lightweight
  reusable client beneath a native custom component, with one per-entry runtime,
  one coordinator, one high-level operation lock, and HA-owned storage.
- The convergence needs several corrections before it becomes a safe plan:
  avoid a duplicate startup poll; account for coordinators becoming idle with
  no listeners; separate profile lineage, last successful application, and
  live match; add store-neutral public result contracts; and preflight
  cross-setting edits against fresh peer values.
- Where the clarified task and local TUI do not determine an HA product rule,
  the plan must carry a specific user-review TODO rather than silently choosing
  a behavior.
- Release metadata, integration domain, minimum HA version, and device identity
  uniqueness are genuine prerequisites, not implementation details to invent.

## Findings

### Local evidence that all proposals should preserve

- `src/wolf_325/__init__.py` and
  `.docs/contracts/controller-api-and-json.md` define the supported client
  boundary. `WolfCWL2`, `RegisterDef`, `REGISTERS`, `ValueState`, typed errors,
  and profile result types should remain the integration's only device-library
  imports.
- `src/wolf_325/register_catalogue.json` is authoritative for 154 logical
  values and their wire/type/safety metadata. It is not authoritative for HA
  platform, device class, state class, entity category, translation, or default
  enablement. A second wire-register table would violate
  `.docs/ARCHITECTURE.md` and `.docs/code-relationships.md`.
- `SettingsMixin.set_settings()` persists desired state before I/O,
  `WriteMixin._write_definition()` normally verifies read-back, and
  `BulkWriteError` reports partial outcomes. These semantics are already tested
  in `tests/test_controller.py` and must not be replaced by optimistic HA state.
- `ProfileLoader.capture_changes()` uses canonical persistent `desired` and the
  exact `last_profile` parent. It does not inspect live values. Save rejects an
  empty delta and a collision without explicit overwrite; success neither
  applies nor selects the profile. This is specified in
  `.docs/workflows/profile-capture.md` and tested in
  `tests/test_profile_capture.py`.
- `TransportMixin._io_lock` serializes only one Modbus request. It does not make
  a tier poll, bulk write, profile apply, or reconciliation indivisible.
  `ControllerTuiService` relies on the TUI's exclusive worker group for this
  higher-level exclusion. HA therefore needs one outer lock per entry.
- `WolfCWL2.start()` always performs an all-tier poll, catches an initial
  `CommunicationError`, may restore, then optionally starts three poll tasks
  and a reconcile task. A coordinator first refresh after an unchanged
  `start(background=False)` would poll twice.
- A transport failure in `PollingMixin._poll_tier()` marks the failed block
  unavailable and aborts. Other cached values may retain `available=True` while
  `controller.connected` is false. HA availability must combine entry health,
  connection state, per-value state, and tier freshness.
- `config.atomic_json_write()` and `read_json()` currently execute their
  synchronous writer/reader on the event-loop thread; profile globbing and
  path checks are also synchronous. The nominally async signatures are not
  enough for HA event-loop safety.
- `SavedProfile.path: Path`, `WolfCWL2(config_path=...)`, direct
  `config_store.update_desired()` calls, and `ProfileLoader` make the current
  public profile/persistence shape filesystem-specific. An async repository
  protocol alone is insufficient unless save results also stop requiring a
  filesystem `Path` (or a distinct store-neutral result is added).
- `validate_cross_settings()` validates only keys present in its mapping.
  `set_settings(persist=False)` merges changes with persistent `desired`, not a
  fresh confirmed appliance baseline. Consequently, an individual temporary
  edit can be valid by itself but produce an invalid live airflow/PWM/CO2/
  analog/geothermal combination. None of the three reports makes this delivery
  gate explicit enough.
- `transport.py` logs host, port, unit ID, and endpoint-bearing exceptions.
  Diagnostics redaction alone will not sanitize logs.
- `pyproject.toml` unconditionally installs Textual and contains no license,
  project URLs, or Home Assistant dependency. There is no custom component,
  HACS metadata, or recorded Git remote. Agent 3 correctly treats public
  repository/owner/license/package-release facts as unresolved release inputs.

### Current Home Assistant convention corrections

- Home Assistant's coordinator guidance supports `always_update=False` when
  coordinator data has meaningful equality and documents a 5-second minimum
  polling interval. Thus volatile raw words, timestamps, and generated-at
  fields must be excluded from coordinator equality, and options must reject
  intervals below 5 seconds rather than silently clamp them.
- A polling `DataUpdateCoordinator` only schedules while it has listeners.
  Persistent reconciliation and availability cannot accidentally stop because
  all entities were disabled. The runtime must hold a coordinator listener for
  the entry lifetime, or use one explicitly owned scheduler that dispatches
  through the coordinator; it must not add a second independent poll loop.
- Use `OptionsFlowWithReload` **or** an options update listener, never both.
  Agent 3's warning about double reload is correct.
- As of the current custom-integration localization guidance, custom
  integrations must ship complete `translations/en.json`; `strings.json` is a
  Core build-time source and must not be relied on by this HACS/manual package.
  The structures proposed by agents 1–3 should therefore remove `strings.json`
  from the custom-component deliverables unless the project later moves into
  Home Assistant Core.
- `manifest.json` needs an immutable directory-matching domain, a custom
  integration version, `config_flow: true`, `iot_class: local_polling`, exact
  released requirements, and an explicit integration type. With one entry per
  appliance, `integration_type: device` is more accurate than `hub`.
- HA action context supports permission checks, but does not prove physical
  human presence. Rejecting “automation context” is not a reliable confirmation
  mechanism. Dangerous actions must rely on explicit server-side gates and be
  documented as accident prevention, not a security boundary.

Relevant current guidance:

- [Fetching data](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Options flow](https://developers.home-assistant.io/docs/core/integration/options_flow/)
- [Custom integration localization](https://developers.home-assistant.io/docs/internationalization/custom_integration/)
- [Permissions](https://developers.home-assistant.io/docs/auth_permissions/)

## Convergence and Conflicts

### Accepted convergence

All three reports support these plan decisions, and local evidence agrees:

1. Build `custom_components/<domain>/` for HACS/manual installation, backed by
   a separately installable, pinned `wolf-325` client release. Do not vendor a
   second controller implementation.
2. Preserve the file-backed CLI/TUI API while adding async host-neutral runtime,
   desired/lineage, and profile repository seams to the public library.
3. One config entry represents one appliance/unit. Each entry owns one
   controller, coordinator, HA Store, operation lock, and immutable serial-based
   identity; entries never share mutable runtime state.
4. Home Assistant is the only periodic scheduler. Controller background poll
   and reconcile tasks remain disabled.
5. Entity state is confirmed cached appliance state. Persistent desired state
   may be queued ahead of it and is exposed only through bounded summary
   diagnostics, not optimistic control state or volatile attributes.
6. Every catalogue key receives exactly one reviewed HA disposition. Only a
   curated subset is enabled by default; wire metadata stays in the canonical
   catalogue and HA semantics live in a separate validated overlay.
7. Profile apply is sequential and may partially succeed. There is no device
   transaction, rollback, or compare-and-swap, and the integration must not
   imply one.
8. The three Modbus communication settings remain read-only diagnostics in v1;
   appliance reset has no ordinary entity or generic raw-register escape hatch.
9. HA owns Recorder history. The controller state file is disabled in HA, and
   raw words, timestamps, desired mappings, profile bodies, and exception text
   stay out of ordinary entity attributes.

### Conflicts and recommended resolutions

| Topic | Conflict | Integrated resolution |
|---|---|---|
| Initial polling | Reports both rely on `start()` and describe a coordinator first refresh, which would duplicate the all-tier read. | Add a backwards-compatible `initial_poll=False` lifecycle option (or equivalent direct initializer) for HA. Let `async_config_entry_first_refresh()` perform the only initial poll and propagate setup retry correctly. CLI/TUI defaults remain unchanged. |
| Coordinator liveness | Reports assume the coordinator always runs. HA stops scheduled polling without listeners. | Keep one entry-lifetime coordinator listener/scheduler. Test persistent reconciliation and reconnect with every entity disabled. |
| Profile capture by mode | Agents 1/2 allow capture in temporary mode from dormant desired state; agent 3 permits it only in persistent mode. The TUI has read-only versus control-enabled mode, not HA's entry-wide temporary mode, so local behavior does not settle this. | Permit list/preview in all modes; reject save in monitor-only exactly like the TUI. Safest v1 default is save only in persistent mode. Add a plan TODO asking whether temporary mode may intentionally capture dormant historical desired state. Never capture temporary writes. |
| Profile select state | Agent 1 uses last successful HA apply; agent 2 makes it a live-match selector with a sentinel; agent 3 conflates last apply and lineage. | The select is a command surface whose state is the last fully successful HA application. Keep persistent `last_profile` solely as capture lineage. Do not claim current match in v1; a separately named drift/sync diagnostic can be added only with an explicit comparison contract. Partial apply never advances last-successful state. Temporary last-successful state is runtime-only after restart. |
| Filter reset | Agents 1/2 propose a button; agent 3 proposes a guarded action. The catalogue says non-dangerous, but the TUI still requires `EXECUTE ACTION`. | Preserve the stronger existing operator guard in v1: action-only, exact phrase, unambiguous target, non-monitor mode. A normal button can be reconsidered as a documented product relaxation. |
| Appliance reset | Proposed gates range from only phrase/option to phrase + serial + admin + “interactive only.” | Require per-entry opt-in default false, control-enabled mode, one target, exact `RESET APPLIANCE`, expected serial, live serial match, and HA control/admin permission. Do not claim automation detection proves human presence. Report only command dispatch, then invalidate/reconnect. |
| Poll cadence | Some reports tick at “fast”; others say shortest enabled cadence. | Tick at the minimum of enabled tier/reconcile intervals, all at least 5 seconds, with monotonic due deadlines and no catch-up burst. This avoids imposing an undocumented `fast <= slow <= static` relation. |
| HA storage split | Agent 3 diagrams separate controller/profile stores; agents 1/2 favor one payload. | Use one versioned Store payload per entry so `desired` + `last_profile` can commit atomically and profile mutations can validate one catalogue revision. Expose separate library protocols/adapters over that single transaction owner if interfaces benefit. |
| Reconciliation retries | Agent 2 adds per-key suspension/Repairs; others retain current indefinite behavior. | Do not silently invent a retry policy in the first implementation slice. Add categorized attempts/backoff and observability first. Make suspension/repair thresholds a reviewed contract TODO; transport backoff must not become a permanent repair issue. |
| Entity metadata format | Reports alternate Python description modules and a large JSON file. | Use a declarative HA-only overlay with a typed loader/validator; JSON is acceptable and is exempt from source LOC limits. Split executable platform/runtime code by responsibility and keep it under 300 lines. |

## Recommended Integrated Architecture and Contracts

### Public library layer

Add, with tests first:

- a direct normalized runtime configuration path that does not require a JSON
  config file;
- async desired/lineage and profile repository protocols with atomic revisioned
  mutations;
- store-neutral profile documents/results (do not require `SavedProfile.path`
  for an HA-backed save);
- store-independent inheritance, whole-catalogue validation, and exact capture
  delta logic reused by file and HA adapters;
- `start(initial_poll=False, restore=False, background=False, read_only=...)`
  or an equivalent explicit initialization sequence;
- a public one-shot reconciliation operation only if existing
  `apply_desired(force=...)` plus public snapshot generation is insufficient;
- nonblocking file adapters (`asyncio.to_thread` for durable filesystem work),
  state-output disablement, sanitized connection/log errors, and reusable
  example-profile data outside `cli_init`; and
- context-aware validation for relational settings. When a relation group is
  touched, compose a candidate from fresh confirmed peer values plus the
  proposed changes. Reject if peers are unavailable/stale. For multi-key
  changes, define safe dependency ordering as well as final-state validation.

Keep `WolfCWL2(config_path=...)`, existing CLI/TUI profile files, and existing
public exports compatible. Move Textual to a `tui` extra and test that base
client import/construction neither imports nor requires Textual.

### Per-entry Home Assistant runtime

One typed `ConfigEntry.runtime_data` contains the controller, coordinator,
single Store transaction owner, outer `asyncio.Lock`, stopping flag, expected
serial, authority mode, tier deadlines, and small desired/profile status
records.

Setup order is strict:

1. Load and migrate the entry Store; reject unsupported/corrupt versions
   without touching the appliance.
2. Construct the controller from entry data/options and injected adapters.
3. Start lifecycle without poll, restore, state file, or background tasks.
4. Run the coordinator first refresh under the outer lock, including static
   identity.
5. Require a valid compatible identity and exact configured serial. Never use
   host as an identity fallback and never restore before this gate.
6. In persistent mode, force-apply desired state, publish confirmed results,
   then forward platforms. A partial restore keeps desired pending and surfaces
   a truthful status; it must not make setup appear as a different device.
7. Hold the coordinator scheduler/listener for the entry lifetime.

Mark the runtime stopping before unload, reject new operations, unload
platforms, drain an active operation within a documented bound derived from
transport/verification settings, stop the controller, and remove listeners.
If safe draining cannot complete, fail unload rather than cancel a compound
profile midway and claim success. Entry removal deletes only that entry's Store.

Use the serial for config-entry unique ID, device identifier, and entity unique
ID prefix. Reconfiguration may change host/port/unit/transport/offset only
after probing the same serial. Two different serials must load as isolated
entries even when they share a gateway.

### Coordinator, polling, and availability

- One coordinator update acquires the outer lock, selects all due tiers from
  monotonic deadlines, calls `poll_once(tiers=due)` once, performs due
  persistent reconciliation, snapshots meaningful state, and releases the
  lock before dispatch.
- Advance deadlines from completion and skip missed cycles; do not burst after
  outage. Use HA retry/backoff for transport failure and preserve per-register
  protocol/optional failures as localized unavailability.
- Set `always_update=False` over a comparable immutable data object that omits
  `generated_at`, raw words, sample timestamps, and exception strings.
- An ordinary register entity is available only if the latest coordinator
  refresh succeeded, the controller is connected, the value is available, and
  its enabled tier is fresh within a documented multiple of its configured
  interval. A successful fast poll must not make a stale slow/static entity
  current.
- Writes, profile operations, capture, resets, and polling all take the same
  outer lock. Entities read memory only and never initiate I/O from properties.
- After a write or partial bulk operation, publish verified cache results and
  refresh only where the controller did not already read back. Never perform an
  unconditional second verification read.

### Entities and Recorder

- Assign exactly one of `sensor`, `binary_sensor`, `number`, `select`, `switch`,
  explicit composite, read-only diagnostic, or action-only/no-entity to every
  catalogue key. Tests fail on missing/duplicate/stale mappings.
- Base the initial default-enabled set on the 19 `OVERVIEW_KEYS`, but review
  every included control and maintenance value. Optional extensions,
  installation settings, identities, raw/debug values, and noisy diagnostics
  default disabled.
- Unique IDs are `<serial>:<canonical-key>` (and stable semantic suffixes for
  synthetic entities). Host, entry ID, display name, mode, and profile name
  never participate. Platform assignment is migration-sensitive.
- Use canonical HA native units/classes. `MEASUREMENT` is only for reviewed
  instantaneous values. Do not assign `TOTAL`/`TOTAL_INCREASING` to the u32
  counters until physical monotonic/reset behavior is validated. Settings and
  setpoints have no statistics class.
- Unknown read enum words stay observable as `unknown_<raw>` on sensor-like
  entities. A writable select offers only documented options and does not make
  an unknown current value writable.
- The four non-restorable date/time components need an explicit composite
  mapping and atomic/user-comprehensible update contract. Do not expose packed
  words as misleading numbers merely to reach full coverage.
- Keep the same entity domain/unique ID across authority-mode changes. In
  monitor-only mode state remains visible, but mutation handlers reject both in
  HA runtime and client read-only guard. Mode is not availability.

### Authority modes

| Contract | Monitor-only | Temporary | Persistent |
|---|---|---|---|
| Poll/Recorder | yes | yes | yes |
| Safe ordinary writes | reject | `persist=False` | `persist=True` if restorable; otherwise temporary |
| Profile apply | reject | temporary settings only | atomic desired/lineage save, then sequential verified writes |
| Startup/reconnect/periodic reconcile | never | never | yes, only after identity verification |
| Filter/appliance reset | reject | guarded, never persisted | guarded, never persisted |
| Desired/profile records | retained inactive | retained inactive | active |
| Capture save | reject | TODO; safest default reject | exact desired/lineage capture |

Changing away from persistent stops enforcement but preserves desired and
lineage. Returning to persistent with dormant desired state must show the exact
pending keys and require an explicit resume/apply or clear-ownership choice; it
must not silently reassert old state. Release ownership is an explicit
operation and does not write a replacement value.

### Profiles and action contracts

Use one per-entry versioned Store document with distinct store schema version
and portable profile-document version. At minimum it owns `revision`,
`desired`, `last_profile`, `profiles`, and `last_successful_ha_profile` where
applicable. Use awaited immediate Store saves, never delayed saves, for the
persistence-before-I/O invariant.

- Persistent apply validates the complete catalogue, saves desired plus lineage
  in one Store revision, then writes sequentially. Failure may leave intended
  ownership pending.
- Temporary apply changes no desired/lineage ownership; `replace` and `unset`
  have no direct device-clearing meaning.
- Capture uses only durable desired and exact `last_profile`, preserves
  inheritance/replace/unset/name/empty-delta/collision semantics, does no
  Modbus I/O, and does not select/apply the new profile.
- Overwrite validates the resulting entire graph, including descendants,
  before one commit. Profile option lists refresh without reloading the entry.
- A capture preview should return the Store revision; save may accept an
  expected revision to reject stale previews.
- `last_profile` is capture lineage. `last_successful_ha_profile` is a UI action
  result. Neither proves current match. Do not add live match inference to v1.
- Register actions once and require an unambiguous loaded config-entry/device
  target. Translate typed validation, communication, verification, partial, and
  persistence outcomes; never expose raw Python exception text.

Direct shared filesystem access, automatic CLI/TUI profile watching, implicit
cross-device profile reuse, and user-facing import/export are v1 non-goals.
Store a versioned portable profile schema so explicit import/export can be
added later without changing capture semantics.

## Phase and Dependency Corrections

1. **Resolve release/product TODOs and record decisions.** Confirm immutable HA
   domain/model scope, license, public Git repository and code owner, PyPI
   ownership/name, minimum HA/Python versions, serial uniqueness evidence,
   packed clock mapping, temporary-mode capture, and reconciliation suspension
   policy. Create the implementation plan only under
   `.docs/plans/active/home-assistant-integration/`.
2. **Make the client host-neutral and safe first.** Tests precede direct config,
   repository protocols, store-neutral results, pure profile logic, initial-poll
   control, relational live-state validation, async file adapters, log
   sanitization, state-file disablement, and optional Textual packaging. Keep
   all existing CLI/TUI tests green.
3. **Release/qualify the client dependency before integration packaging.** Add
   license/project metadata, build a wheel, test clean base import without
   Textual, qualify the exact PyModbus pin against the chosen HA environment,
   publish the client, then reference that real exact version in the manifest.
4. **Land multi-entry monitoring lifecycle.** Scaffold manifest/HACS metadata,
   `translations/en.json`, config/reconfigure/options flows, one Store/runtime/
   lock/coordinator, no-double-poll setup, serial verification, cleanup,
   listener-independent scheduling, diagnostics skeleton, and two-entry tests.
5. **Land the complete read surface before controls.** Approve the exhaustive HA
   overlay, curated defaults, stable IDs, availability/freshness, unknown enums,
   date/time composites, and Recorder semantics. Begin with read-only platforms.
6. **Land controls and persistence.** Add mode guards, confirmed ordinary
   writes, relational preflight, reconnect/startup reconciliation, mode
   transitions, desired-sync diagnostics, release ownership, and guarded filter
   action.
7. **Land profiles, then appliance reset.** Add apply/select, exact capture,
   revisions/overwrite graph validation, dynamic options, partial failures, and
   finally the opt-in multi-gate appliance-reset action/reconnect behavior.
8. **Operational/release hardening.** Add redacted diagnostics/log tests,
   actionable repairs only, HACS/hassfest/manifest/translation checks, manual
   install and HACS custom-repository smoke tests, unload/leak tests, user docs,
   and read-only physical validation. HACS publication cannot complete before
   the repository/release inputs and pinned client artifact exist.

Each closed phase should update its owning system-of-record records and form an
atomic commit. Never push. Do not physically test writes or resets without the
existing workflow's explicit target, original value, restoration, and recovery
authorization.

## Explicit Non-goals for v1

- Home Assistant Core submission itself, discovery, TLS/authentication, an
  add-on, MQTT/API bridge, or a second protocol implementation.
- Shared live profile files or cross-process locking with CLI/TUI.
- Automatic profile import/export or cross-device catalogue synchronization.
- Writable Modbus interface/address/speed controls or a generic raw-register
  service.
- A claim of atomic/rollback profile application or prevention of external
  local-panel/TUI/second-instance writers.
- Live profile-match inference, automatic selection among matching partial
  profiles, or capture from arbitrary live registers.
- Long-term-statistics classes for unvalidated counters.
- Routine physical filter/appliance resets, communication writes, or profile
  applications.

## Plan TODOs That Must Not Be Guessed

- **TODO: Confirm the immutable integration domain and supported model scope.**
  `wolf_cwl2` and `wolf_325` have different future compatibility implications.
- **TODO: Decide whether temporary mode may save profiles from dormant desired
  ownership.** Exact capture content is settled; the entry-mode permission is
  not represented by the TUI contract.
- **TODO: Approve the HA mapping for the four writable non-restorable date/time
  components.** A composite date/time action is preferable, but timezone,
  weekday, and partial-write failure semantics require product review.
- **TODO: Establish a measured polling lower bound at or above HA's 5-second
  minimum and a freshness multiplier.** The current 5/60/300 defaults remain
  provisional evidence, not a guarantee that every gateway supports 5 seconds.
- **TODO: Validate serial uniqueness/stability and compatible appliance-type
  values on physical evidence.** Do not introduce a host fallback if this fails;
  redesign identity before release.
- **TODO: Choose bounded persistent-mismatch retry/suspension and Repair issue
  thresholds.** Do not inherit infinite write churn or invent thresholds.
- **TODO: Supply license, public repository/issue/documentation URLs, GitHub code
  owner, PyPI owner, minimum HA release, and supported Python versions.** These
  block publishable package/HACS metadata.
- **TODO: Approve the exact default-enabled entity list and every counter's
  Recorder class after metadata and physical review.** `OVERVIEW_KEYS` is useful
  evidence, not a complete product decision.

## Risks

- Persistent mode can intentionally overwrite local-panel or other-controller
  drift; stale dormant desired state makes mode re-entry especially hazardous.
- HA serialization prevents only local interleaving. External writers and two
  HA instances remain last-writer races.
- An HA Store adapter that uses delayed saves, separate nontransactional stores,
  or filesystem-shaped profile results would break persistence-before-I/O or
  future Core portability.
- Custom integration and client versions are distinct release artifacts. A
  manifest pin to an unpublished or Textual-dependent wheel makes installation
  fail even if repository tests pass.
- Incorrect platform/unit/state-class changes can fragment entity history and
  long-term statistics. Mapping changes need migrations and release notes.
- A profile selector that reports lineage or inferred match as current device
  truth will mislead users after partial apply, normalization, or external
  drift.
- Broad enabled polling still reads blocks even when individual entities are
  disabled; curated defaults reduce Recorder/UI noise but not necessarily
  Modbus load.
- Confirmation strings are reproducible by automations. The reset option,
  permissions, serial match, and recovery documentation remain essential.

## Validation Gates

### Client gates

- Existing full `uv run pytest` suite passes with unchanged file/CLI/TUI
  behavior and new injected repositories.
- File and HA-neutral repositories produce identical profile resolution,
  capture, replace/unset, names, cycles, collisions, and full-graph validation.
- Desired plus lineage is durably committed once before the first persistent
  write; temporary operations make no repository mutation.
- Initial-poll suppression causes no hidden poll; state output can be disabled;
  filesystem work is off-loop; clean base import needs no Textual.
- Relational single/bulk edits test fresh peers, unavailable peers, safe write
  order, and no persistence/I/O after failed preflight.
- Logs and public errors contain no sentinel host, port, serial, profile text,
  or endpoint-bearing exception data.

### Home Assistant lifecycle gates

- Config flow handles cannot-connect/incompatible/duplicate identity; two
  serials produce isolated entries; reconfigure rejects a changed serial.
- Exactly one initial all-tier poll occurs, no controller background task runs,
  and tier/reconcile deadlines are deterministic under fake monotonic time.
- Poll/reconcile continues with all entities disabled; there is no catch-up
  burst; setup failure, reload, unload, and removal leak no tasks/transports.
- One blocked fake gateway proves that poll, write, reconcile, profile, capture,
  and reset never interleave within an entry while another entry remains live.
- A transport loss makes all device values unavailable immediately; optional
  register failures remain local; slow/static staleness is not hidden by a
  successful fast update.

### Entity and Recorder gates

- All 154 keys have one disposition; mappings reference real keys; the three
  communication settings and appliance reset have no normal write entity; no
  generic write escape hatch exists.
- Registry/device/entity IDs survive host, title, mode, interval, profile, and
  reload changes and do not collide across two appliances.
- Units, device classes, state classes, precision, unknown enums, defaults, and
  date/time behavior are snapshot/behavior tested. Unproven counters have no
  statistics class.
- No entity has forced updates or volatile raw/timestamp/error/desired/profile
  attributes. `always_update=False` suppresses unchanged-state dispatch.

### Control/profile/action gates

- A matrix covers all modes and every mutation path, including entity calls,
  release, reconcile, profile apply/capture, filter reset, appliance reset, and
  calls racing unload/mode change.
- Confirmed state never becomes the requested value before read-back.
  Persistent failures explicitly remain queued; temporary failures do not.
- Startup/reconnect restore occurs only after live serial verification.
  Dormant-state reactivation requires the chosen explicit transition.
- Profile tests cover HA Store schema/revision, inheritance, replace/unset,
  whole-graph overwrite validation, empty delta, collisions, partial apply,
  last-successful versus lineage, temporary exclusion, and option refresh.
- Reset tests reject disabled option, monitor-only, ambiguity, wrong phrase,
  wrong serial, stale live identity, and insufficient permission. Accepted
  appliance reset reports only dispatch and enters unavailable/reconnect state.

### Packaging, documentation, and physical gates

- Validate wheel, exact manifest requirement, HACS metadata, `translations/en.json`,
  service/action schema, diagnostics, minimum-HA test environment, hassfest/HACS
  validation, and clean manual/HACS installation.
- Update `.docs/ARCHITECTURE.md`, `.docs/code-relationships.md`, the controller
  contract, controller domain, profile workflow, new HA config/storage/action
  contracts, one-owner/storage/package decisions, HA operation/install-release
  workflows, physical-validation cross-links, and README at the phase that owns
  each fact.
- Physical validation begins monitor-only and read-only: identity, complete
  mapping, availability, cadence/load, disconnect/reconnect, and Recorder
  semantics. Any write/profile/reset validation requires separate explicit
  authorization and restoration/recovery evidence.
