# Home Assistant Integration

Purpose: Perspective exploration before solving.

## Source Task

**Task title:** Home Assistant integration for WOLF CWL-2 control
**Captured:** 2026-08-11T10:04:01+02:00

> I want this device control to be usable in Home Assistant, including the
> individual controls, settings and datapoints, with automatic refresh so data
> can be plotted as time series. Profile selection should apply multiple
> settings at once. Ideally, the Home Assistant integration should also save
> current settings to a new profile, similar to the TUI application.

The user explicitly requested `$think-with-agents` first and
`$implementation-plan` second. This session is analysis and planning only; it
does not authorize implementation.

## Chain-of-Thought Summary

- The requested surface spans telemetry, control entities, multi-setting
  profile actions, and profile-file creation, so integration architecture and
  ownership boundaries materially affect the plan.
- Repository constraints include modular source files under 300 lines, TDD,
  atomic/profile safety behavior, accurate system-of-record documentation, and
  `uv`-managed Python commands.
- The planning output must live under `.docs/plans/active/` because the local
  plan-location rule overrides the planning skill's default `.plan/` path.
- The repository already has a capable async controller and metadata catalogue,
  but no Home Assistant component or Home Assistant semantic metadata.
- Controller-owned polling/reconciliation and Home Assistant-owned coordination
  are both technically plausible; running both would duplicate work and create
  unclear lifecycle ownership.
- Current profile capture records persistent desired ownership, not a live
  device snapshot, which is the most consequential ambiguity in “save current
  settings.”

## Findings

- The initial perspective agent must first assess the problem without assuming
  this repository, then inspect the local controller, polling, profiles, CLI,
  TUI, tests, and architecture records.
- Material questions likely include Home Assistant deployment/distribution
  model, configuration UX, entity exposure policy, write safety, polling
  ownership, and whether profile files live on the Home Assistant host.

## Running Log

- Session file created.
- Original task and immediate repository/planning constraints recorded.

## Pass 1 — General Perspective

This pass treats the request as a product and integration problem without
assuming anything about the repository's language, transport, or current
abstractions.

### Desired outcomes and stakeholders

- A Home Assistant operator needs current measurements to appear reliably,
  become unavailable rather than silently stale when communication fails, and
  retain stable identity/units/device classes so Recorder, statistics, graphs,
  dashboards, and automations continue to work across upgrades.
- A person changing ventilation settings needs writes to be explicit,
  validated, and observable: optimistic UI can feel responsive, but confirmed
  device state must ultimately win and write failures must be visible.
- A profile user needs a single understandable operation that changes several
  related values with known ordering, partial-failure behavior, and feedback
  about whether the device now matches the selected profile.
- An administrator needs a low-friction setup and reauthentication path,
  predictable network load, useful diagnostics, and a supported upgrade and
  distribution story.
- Maintainers need one testable boundary around the device protocol and clear
  ownership between any reusable client library and Home Assistant-specific
  lifecycle/entity behavior.

### Ambiguities and decisions still hidden in the request

- “Usable in Home Assistant” could mean a native custom integration, an
  add-on/service bridged through MQTT, command-line/shell exposure, or an
  upstream-core-quality integration. These categories differ sharply in
  installation, review constraints, dependency isolation, and long-term
  maintenance.
- “Individual controls, settings and datapoints” does not define the supported
  matrix. Some raw values may be diagnostic, write-only, unsafe, enum-like,
  composite, rarely changing, or unsuitable as first-class entities.
- “Automatic refresh” leaves cadence, backoff, batching, push-versus-poll,
  startup behavior, and the owner of the connection unspecified. A refresh
  suitable for live dashboards may be unnecessarily aggressive for historical
  plotting or the device bus.
- “Profile selection” might mean selecting a persistent desired mode, invoking
  a one-shot scene-like action, or applying a bundle and then allowing manual
  drift. The correct entity/service semantics depend on that distinction.
- “Save current settings as a new profile” leaves name validation, overwrite
  policy, scope, author, timestamps, schema/version lineage, secrets,
  diagnostics, and storage destination unresolved. Home Assistant service calls
  also lack the interactive prompts a TUI may rely upon.
- Multiple Home Assistant instances, the existing TUI, or another controller
  may write concurrently. It is unclear whether the device is single-writer,
  whether writes carry revisions, and how drift or external changes are
  detected.

### Lifecycle, polling, and history concerns

- Home Assistant normally benefits from a single per-device update owner that
  batches reads and fans one coherent snapshot out to entities. Independent
  entity polling is another possible category but risks redundant traffic,
  inconsistent timestamps, connection contention, and rate-limit pressure.
- Refresh needs distinct notions of scan interval, request timeout, snapshot
  timestamp, last successful contact, retry/backoff, and staleness. Reporting
  old values as current after disconnect is especially harmful for automations
  and time-series interpretation.
- Recorder compatibility is semantic, not merely “a numeric state.” Stable
  entity IDs/unique IDs, correct native units, device/state classes, bounded
  enum states, sane precision, and avoiding volatile attributes all affect
  long-term statistics and database growth.
- Some data belongs in entity state; high-cardinality debug metadata generally
  should not be attached to every state update. Fast-changing points may need a
  different default cadence or opt-in enablement to avoid overwhelming either
  the appliance or Recorder.
- A push-capable protocol, if one exists, still needs reconnect, initial
  snapshot, missed-event recovery, and probably a periodic consistency read.

### Controls and desired-state reconciliation

- Entity types should follow user meaning rather than raw register shape:
  measurements, switches, numbers, selects, binary sensors, buttons, and
  diagnostic entities communicate different capabilities to Home Assistant.
- Bounds, steps, units, enum choices, prerequisites, and mutual exclusions must
  be represented and revalidated at write time. A UI range alone is not a
  safety boundary.
- A write policy must decide between confirmed-state updates and optimistic
  state. Either way, a subsequent read-back should distinguish accepted,
  normalized/clamped, rejected, timed-out, and superseded writes.
- Serializing writes through the same connection/update owner can prevent a
  poll from racing a change. Coalescing or debouncing may help some controls but
  can be unsafe where each command is meaningful.
- Availability should separate whole-device failure from unsupported or
  temporarily inaccessible values. Authentication failure, protocol failure,
  invalid response, and profile partial failure deserve actionable but
  privacy-safe diagnostics.

### Profile semantics and lineage

- Plausible profile categories include files shipped with the client,
  integration-managed persistent records, Home Assistant-native scenes/scripts,
  or profiles managed by a separate controller. The storage owner determines
  portability, backup behavior, permissions, and whether the TUI and Home
  Assistant see the same catalog.
- Profile application needs a declared field set, deterministic validation,
  preflight against current device capabilities, ordering or dependency rules,
  and a defined response when one write fails. “Atomic” may be impossible at
  the device level; compensating rollback can itself fail and must not be
  implied without evidence.
- “Selected profile” and “device matches profile” are different facts. Manual
  changes or device-side normalization can create drift immediately after an
  apply; exposing a selected name as durable device state could therefore be
  misleading.
- Capturing a profile should use a coherent, confirmed snapshot and an explicit
  allowlist of writable, portable settings. Read-only telemetry, volatile
  counters, credentials, connection details, and transient status should not be
  copied merely because they are present in the current snapshot.
- Lineage questions include whether capture records the source device/model,
  firmware/capability revision, parent profile, creation time, and schema
  version; and what happens when a profile is applied to a different model or
  newer firmware.

### Connection, configuration, packaging, and operations

- Setup choices include host discovery versus manual address, credentials or
  pairing, TLS/certificate expectations, connection testing, duplicate-device
  prevention, options for polling, and a repair/reconfigure flow when the host
  or authentication changes.
- A device registry identity must survive DHCP/address changes without
  collapsing two physical units into one. The available protocol identity
  therefore constrains configuration UX and stable entity identity.
- Distribution categories—Home Assistant Core, HACS/custom component, add-on,
  or external bridge—carry different manifest, dependency, release,
  localization, security, and support obligations. The target has to be chosen
  before packaging work can be scoped credibly.
- Useful operations include structured logs without secrets, downloadable
  redacted diagnostics, communication/error counters, firmware/model context,
  and repair guidance. Debug data should not create noisy Recorder entities by
  default.
- Testability requires transport fakes at the external boundary, deterministic
  snapshots, failure injection for timeouts/partial writes/reconnects, entity
  contract tests, lifecycle setup/unload/reload tests, migration tests for
  identifiers/options/storage, and profile validation/capture round trips.

### Risks, tensions, and plausible solution-path categories

- A direct native integration offers the most natural device/entity/config-flow
  experience, while a broker or external-service path can isolate a blocking or
  unusual protocol. A thin command wrapper is cheaper initially but commonly
  weak on lifecycle, availability, diagnostics, and coherent updates.
- Broad automatic exposure maximizes completeness but can create a confusing UI,
  unstable contracts, unsafe controls, and excessive history. A curated default
  surface with optional advanced/diagnostic entities trades discoverability for
  safety and maintainability.
- Faster polling improves apparent freshness but increases device/network load
  and Recorder churn. The actual protocol cost and operator time-resolution
  requirements are prerequisites to choosing a default.
- Shared profile files could preserve TUI parity but couple Home Assistant to
  filesystem layout and locking. Separate integration storage improves
  lifecycle ownership but creates import/export and catalog divergence issues.
- Reusing an existing client API could reduce duplication, but only if its
  concurrency, error, snapshot, and packaging contracts fit Home Assistant.
  Otherwise an adapter or extracted library boundary may be needed; this cannot
  be decided without local evidence.

### Questions that evidence should answer before asking the user

- What protocol/client and synchronization model already exist, and can one
  client instance safely serve repeated reads plus serialized writes?
- Which datapoints are readable, writable, typed, bounded, unit-bearing, or
  grouped, and which are already treated as unsafe or excluded?
- Are refresh, read-back, retry, atomic profile application, and rollback
  behaviors already implemented and tested?
- What exactly constitutes a profile today, where is it stored, and how does
  the TUI capture, validate, name, and overwrite it?
- Is the project already packaged as a reusable library, and are there durable
  architecture/contracts that constrain a Home Assistant adapter?

## Pass 2 — Local Resource Perspective

### Existing foundation and public boundary

- This is already an async Python 3.11+ Modbus client for a CWL-2-325 behind a
  Waveshare TCP-to-RTU gateway, not a command-only prototype. `README.md` and
  `.docs/ARCHITECTURE.md` describe tiered polling, callbacks, cached snapshots,
  verified named writes, persistent desired-state reconciliation, profiles,
  CLI, and TUI.
- `src/wolf_325/register_catalogue.json` contains 154 definitions: 44 fast, 90
  slow, 18 static, and 2 never-polled; 78 are writable, 69 restorable, 4
  dangerous, 2 one-shot, and 40 optional. `RegisterDef` in
  `src/wolf_325/register.py` carries key, description, table/address, codec,
  count, scale, unit, enum, bounds, step, and the operational flags. This is a
  substantial reusable source for entity generation rather than a reason to
  hand-maintain a second register table.
- The declared compatibility surface is `src/wolf_325/__init__.py` and
  `.docs/contracts/controller-api-and-json.md`. It publicly exports `WolfCWL2`,
  `REGISTERS`/`REGISTER_LIST`, `RegisterDef`, `ValueState`, profile result
  types, and typed domain errors. A Home Assistant layer can therefore use the
  stable facade and catalogue without importing PyModbus internals.
- `WolfCWL2.snapshot()`, `get_state()`, `subscribe()`, and `updates()` in
  `src/wolf_325/controller.py` already expose isolated JSON-compatible state.
  `ValueState.as_dict()` in `src/wolf_325/state.py` provides `value`, `raw`,
  `unit`, `available`, `updated_at`, and `error`. The snapshot also exposes
  connection generation/error, per-tier poll completion times, desired state,
  and `last_profile`.
- The TUI offers useful product evidence, not a ready-made Home Assistant
  adapter. `OVERVIEW_KEYS` in `src/wolf_325/tui_views.py` identifies 19
  high-signal values, while `REGISTER_SECTIONS` in
  `src/wolf_325/tui_navigation.py` partitions all 154 values by operator domain.
  However, `.docs/ARCHITECTURE.md` makes `ControllerTuiService` a TUI-specific
  safety/presentation adapter; it formats textual previews and imports TUI
  editor models, so reusing the public controller boundary is cleaner than
  treating that service as a generic integration API.

### Lifecycle and polling ownership

- `WolfCWL2.start()` performs an initial `poll_once()` and can then create three
  independent tier loops plus a reconcile loop. Defaults in `DEFAULT_CONFIG`
  (`src/wolf_325/config.py`) are 5 seconds fast, 60 seconds slow, 300 seconds
  static, and 30 seconds reconcile. `stop()` cancels all tasks, closes the
  client under `_io_lock`, and writes the final snapshot. Double start/stop and
  cleanup are covered by `tests/test_runtime_edges.py`.
- `poll_once(tiers=...)` and `refresh(name)` are public, so Home Assistant could
  own scheduling, while `start(background=True)` plus callbacks supports a
  controller-owned scheduling category. `ControllerTuiService.start()` shows a
  precedent for `restore=False` with selectable background polling. The future
  integration must select exactly one poll owner per device; otherwise Home
  Assistant coordinator updates and the controller's three loops would both
  read the same gateway.
- Merely passing `restore=False` does not disable later enforcement. With
  background control enabled, `_reconcile_loop()` can force desired values on a
  new connection generation when `restore_on_reconnect` is true and can enforce
  mismatches periodically. This is documented for the TUI in
  `.docs/workflows/tui-operation.md`, but it would be surprising during Home
  Assistant setup unless made an explicit ownership policy.
- `TransportMixin._request()` in `src/wolf_325/transport.py` serializes every
  Modbus request with `_io_lock`, reconnects with bounded request retries, and
  distinguishes remote Modbus rejection from transport loss. This is a good
  concurrency primitive for shared polling and writes, though the lock covers
  individual requests rather than an entire multi-register operation or full
  multi-block snapshot.
- Poll callbacks fire only when value/raw/availability/error changes;
  `updated_at` advances on an unchanged successful read without an emitted
  update (`PollingMixin._update_value()`). A push-style HA adapter therefore
  receives meaningful state transitions but not a notification for every
  successful sampling timestamp. A coordinator-style adapter can publish after
  the requested poll completes.
- Availability is already value-aware: optional block failures can isolate one
  definition, decode failures are cached, and transport failure closes the
  connection. Tests in `tests/test_transport_polling.py` cover short optional
  responses, protocol errors, disconnects, and fallback reads. There is still a
  policy gap for Home Assistant: on a transport failure `_poll_tier()` marks
  the current failed block unavailable and aborts that tier, so values in later
  blocks or other tiers can retain old `available=True` state while global
  `connected` is false. Disabled tiers likewise retain their last state. Entity
  availability must deliberately combine device connectivity, per-value
  availability, and possibly age rather than copy one flag uncritically.
- `_poll_loop()` logs and contains expected communication errors; an unexpected
  exception reaches its outer handler and ends that tier task. Task health,
  consecutive-failure counts, and staleness thresholds are not public
  diagnostics today. `last_connection_error` and `last_poll_at` are useful but
  incomplete for HA repairs/diagnostics.

### Entity modeling and Recorder compatibility

- The catalogue can drive basic platform choice: enum values are plausible
  selects or enum sensors, boolean values switches/binary sensors, bounded
  numeric values numbers/sensors, and the two one-shot registers buttons.
  `build_editor_spec()` in `src/wolf_325/tui_models.py` demonstrates that
  metadata-derived mapping and correctly treats packed date/time codecs and the
  asymmetric `standby_command` specially.
- The catalogue does not contain Home Assistant semantics: device class, state
  class, entity category, default-enabled policy, icon, translation key,
  suggested display precision, diagnostic classification, or long-term
  statistics eligibility. Those cannot safely be inferred from numeric type
  alone. For example, temperatures, instantaneous airflow, accumulated `u32`
  counters, PWM percentages, enum statuses, firmware strings, and packed clock
  components need different Recorder treatment even when their wire type is
  similar.
- Units span `°C`, `K`, `%`, `Pa`, `V`, `ppm`, `rpm`, `m³/h`, `m³`, `kg/h`,
  `h`, and `days`, while 82 values have no unit. Their mapping to Home Assistant
  canonical unit/device-class constants, statistics normalization, and display
  precision needs an explicit compatibility layer. Raw Modbus words belong in
  diagnostics, not changing state attributes that would inflate Recorder.
- Enum decoding intentionally preserves unknown future values as
  `unknown_<raw>` (`.docs/domains/cwl2-controller.md`). That is useful for
  observability but can conflict with a select entity whose option list is
  fixed to the documented enum. Read-side and write-side behavior need to stay
  valid when firmware introduces an unknown state.
- Exposing all 154 definitions is technically possible, but 154 always-enabled
  entities—many optional, static, identity, packed, or advanced installation
  settings—would be noisy. `OVERVIEW_KEYS` and the complete TUI taxonomy are
  evidence for a curated/default-disabled policy, not proof of which entities
  Recorder users want. The requested “individual” exposure and acceptable
  default entity count remain product decisions.
- `serial_number`, `base_software_version`, `base_hardware_version`, and
  `appliance_type` are required static identity values in the catalogue and are
  physically validated by `.docs/workflows/physical-device-validation.md`.
  The 12-digit serial is a promising stable device/config-entry identifier,
  but it is learned only after a successful connection and must be handled
  carefully during initial setup, DHCP host changes, and duplicate-device
  detection.

### Write safety, ownership, and reconciliation

- The existing write path is materially safer than raw register calls.
  `SettingsMixin.set_settings()` in `src/wolf_325/settings.py` normalizes all
  submitted values, validates cross-setting constraints, persists desired state
  before I/O, orders activation-sensitive registers last, and reports partial
  failure through `BulkWriteError`. `WriteMixin._write_definition()` in
  `src/wolf_325/writes.py` performs read-back verification with scale-aware
  comparison. These behaviors and offline queuing are covered in
  `tests/test_controller.py`.
- Persistence-before-I/O is an important UI semantic: an offline entity write
  can raise an error while the requested value remains in `desired` for later
  restoration. Home Assistant must not optimistically present that as confirmed
  device state; it may also need to expose that a desired value is pending or
  differs from the cached device value.
- The largest unresolved control decision is `persist`. Public setters default
  to `persist=True`, which makes Home Assistant an owner that can restore and
  reassert values after local-panel or third-party changes. Using
  `persist=False` avoids that authority but loses desired-state lineage,
  reconnect restoration, and TUI-equivalent profile capture for ordinary HA
  changes. This is both a safety policy and a user-visible meaning of every
  control entity.
- Request serialization does not make `set_settings()` atomic. Its
  multi-register writes are sequential and another poll or write can run
  between requests. `BulkWriteError.results/errors` accurately reports partial
  application, and the desired bundle remains queued, but there is no device
  transaction or rollback. The TUI reduces high-level races through an
  exclusive worker group (`.docs/contracts/controller-api-and-json.md`); a Home
  Assistant adapter would need an equivalent operation-ownership policy for
  concurrent entity and profile calls.
- Four catalogue writes are dangerous: three static Modbus communication
  settings plus the appliance-reset action; filter reset is the other one-shot
  action. The TUI requires exact phrases and permits dangerous communication
  writes only temporarily (`ControllerTuiService.write_register()`). Standard
  HA entity calls have no equivalent confirmation dialog, so “all controls”
  cannot automatically mean enabling these by default.
- Four writable date/time components are intentionally non-restorable, and all
  other non-dangerous restorable settings participate in the persistent model.
  This distinction should survive entity generation rather than treating all
  78 writable definitions identically.

### Profile application, lineage, storage, and capture

- `ProfileLoader` in `src/wolf_325/profiles.py` already supports safe profile
  names, recursive inheritance, ordered parents, merge/replace, `unset`, cycle
  and path-escape rejection, restorable-setting validation, deterministic
  deltas, collision guards, and atomic JSON replacement. Five examples live in
  `profiles/`, and the same documents are generated by `EXAMPLE_PROFILES` in
  `src/wolf_325/cli_init.py`.
- `WolfCWL2.list_profiles()`, `preview_profile()`, and `apply_profile()` are
  directly reusable public operations. Profile application is a validated
  sequential bulk write, not an atomic appliance transaction. A persistent
  apply sets `last_profile` before/with device writes because it persists the
  full desired bundle first; a partial device failure can therefore leave the
  lineage marker and desired state ahead of the confirmed device state.
- A profile-select UI must not imply that `last_profile` means “currently
  matches.” Persistent manual edits and desired-key releases intentionally
  retain the marker so it can act as capture parent, and device normalization or
  external writes can create further drift. The exact contract is documented
  in `.docs/workflows/profile-capture.md` and tested in
  `tests/test_profile_capture.py`.
- Most importantly, existing “save current settings” behavior does **not** read
  the live appliance. `preview_profile_changes()` and `save_profile()` capture
  the canonical persistent `desired` mapping relative to `last_profile`.
  Temporary writes, unowned live holding-register values, and telemetry are
  excluded. This matches the TUI implementation, but the original wording may
  be interpreted as a live snapshot; that semantic must be confirmed before a
  plan promises parity.
- Capture requires a nonempty desired delta, a suffix-free name, optional
  description, and explicit overwrite. It saves but does not apply or select
  the new profile. A new name cannot be expressed by a simple button, and a
  profile select's option list must refresh after file creation, so Home
  Assistant action/service UX and entity UX have distinct roles here.
- Profiles and `last_profile` are filesystem/config lineage. `profiles_dir` is
  resolved relative to the controller JSON file, and locks are per
  `ProfileLoader`/`ConfigStore` instance only. Sharing the same files between
  Home Assistant, the CLI, and the TUI would preserve one catalogue but permits
  cross-process stale reads and last-writer races; separate HA storage avoids
  those races but splits catalogues and requires explicit import/export or
  migration semantics.

### Configuration, packaging, and distribution gaps

- `WolfCWL2` currently requires a path to an existing schema-version-1 JSON
  config. `ConfigStore` deep-merges defaults and owns desired/profile/state
  paths; there is no constructor accepting Home Assistant config-entry data and
  no public client factory. Connection fields cover host, port, device ID,
  address offset, Modbus-TCP versus RTU-over-TCP, timeout, retries, and reconnect
  delays. There is no discovery, authentication, TLS, or reauthentication flow
  in the repository.
- `state_file` defaults to a complete `wolf_state.json` snapshot and is written
  after changed polls, writes, start, and stop. Home Assistant already has
  Recorder and diagnostics, so duplicating this persistence needs an explicit
  purpose or should be disabled through the existing null/empty configuration
  contract.
- Despite async signatures, `read_json()` and `atomic_json_write()` in
  `src/wolf_325/config.py` execute filesystem reads, JSON serialization, flush,
  `fsync`, and replacement synchronously on the event-loop thread. Profile
  listing also performs synchronous filesystem traversal. This was acceptable
  to current tests/TUI but is a Home Assistant event-loop/blocking-I/O concern,
  especially if desired/profile/state files remain part of runtime behavior.
- `pyproject.toml` defines the installable `wolf-325` 0.1.0 distribution with
  `pymodbus==3.14.0` and mandatory `textual>=8.2,<9`. No Home Assistant
  dependency, component manifest, `config_flow`, platform modules, services,
  translations, diagnostics, repairs, or HACS metadata exists. Textual is not
  imported by the stable controller surface, but it is still an unconditional
  package dependency; dependency isolation and PyModbus-version compatibility
  matter if Home Assistant installs this project as a library.
- The repository does not state that `wolf-325` is published to a package
  index, and `pyproject.toml` has no project URLs or license metadata. A custom
  integration that depends on a release, one that vendors/contains the client,
  and an external bridge are therefore materially different packaging paths.
  The target distribution model must precede a credible release workflow.
- Current system-of-record boundaries know only the library, CLI, and TUI.
  `.docs/ARCHITECTURE.md`, `.docs/code-relationships.md`, the controller/API
  contract, and relevant workflows would all need precise Home Assistant
  ownership/dependency updates during implementation; a generic completion note
  would not satisfy the repository's documentation rules.

### Diagnostics, operational safety, and testability

- Existing logging uses `wolf_325`, records connection generations and failures,
  and caches per-value errors. There is no redacted diagnostics export, repair
  issue model, polling/task-health metric, or integration availability summary.
  Endpoint configuration and live serial/state need deliberate redaction rules;
  `.docs/workflows/physical-device-validation.md` already treats the serial and
  gateway password as sensitive operational evidence.
- The deterministic `FakeClient`/`FakeResponse` boundary in
  `tests/conftest.py` is reusable test infrastructure. Current tests exercise
  real codecs/catalogue/config/profiles/controller behavior while replacing
  only the external gateway, including retries, optional values, callback
  backpressure, verification, partial bulk writes, restoration, profile
  lineage, and TUI safety. This aligns well with repository TDD rules.
- There is no Home Assistant test harness or dependency today. New coverage
  would need to add behavior tests before implementation for setup/unload/reload,
  duplicate device identity, one poll owner, coordinator or push recovery,
  entity descriptions and unique IDs, per-value availability, Recorder/state
  class rules, disabled optional/diagnostic entities, confirmed writes,
  persistent-versus-temporary policy, concurrent profile/entity operations,
  profile option refresh and capture failures, config/options flow, migrations,
  diagnostics redaction, and dependency/package loading.
- Physical tests in `tests/hardware/test_read_all.py` are opt-in and read-only.
  The validated 154-register baseline is valuable entity evidence, but no live
  write or profile test is implicitly authorized; the existing workflow
  requires explicit user selection of any physical write target and restore
  value.

### Grounded solution-path categories, without selecting one

- A native Home Assistant adapter around the public `WolfCWL2` facade reuses the
  most behavior, but must reconcile config-entry/storage conventions, async
  filesystem rules, dependency packaging, and polling/reconcile ownership.
- A Home Assistant component containing or vendoring controller modules avoids
  relying on an unpublished distribution but creates duplicated release and
  upstream-sync responsibilities unless the repository layout is deliberately
  reorganized.
- An external daemon/bridge could reuse `WolfCWL2.start(background=True)` almost
  unchanged and isolate dependencies, but would need a new stable protocol
  (commonly broker/API based) and would weaken native config/entity/diagnostic
  experience. No such broker/API exists locally.
- Within a native adapter, controller-owned tier loops with change callbacks and
  Home Assistant-owned scheduled `poll_once(tiers=...)` are both supported by
  the public API. The former preserves tier cadence/reconcile behavior; the
  latter fits a single host lifecycle but needs an explicit strategy for mixed
  fast/slow/static cadence. Evidence does not justify choosing between them in
  this perspective pass.

### Handoff: questions that truly require user clarification

The repository answers most protocol and capability questions. The remaining
product choices that materially change the future plan are:

1. Is the intended deliverable a local/HACS-style custom integration, an
   upstream Home Assistant Core candidate, or an external add-on/bridge?
2. Should normal Home Assistant control changes be persistent owned desired
   state that is restored/reconciled, temporary direct changes, or a user
   option? May the TUI/local panel/another controller also write the appliance?
3. Does profile capture mean exact TUI parity—save persistent `desired` deltas
   relative to `last_profile`—or a new live-device capture of currently readable
   restorable settings?
4. Must Home Assistant and the TUI/CLI share one profile catalogue and lineage,
   or may Home Assistant own separate storage with import/export?
5. Should all 154 values and 78 writes be creatable with advanced/optional ones
   disabled by default, or is a smaller supported surface acceptable? In
   particular, should dangerous Modbus configuration and appliance-reset
   operations be omitted, service-only, or explicitly opt-in?
6. Is support for multiple CWL-2 devices/config entries required from the first
   release, and what time resolution is actually needed for plotted fast values
   versus slower settings/counters?

These questions should be resolved before choosing lifecycle, storage, entity,
and distribution work packages; exact register mappings and failure behavior
can be derived from the existing catalogue, contracts, and tests without more
user input.
