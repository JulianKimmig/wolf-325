# Home Assistant integration reasoning — Agent 2

## Source Task

Plan, but do not implement, a native Home Assistant custom integration for the
public `wolf_325` / `WolfCWL2` API. The first distribution target is manual
installation and HACS, with a credible path toward Home Assistant Core. The
integration must support multiple config entries/devices, automatic polling for
Recorder-compatible histories, a curated default entity surface while defining
all supported catalogue datapoints, per-entry monitor-only/temporary/persistent
control modes, Home Assistant-owned profiles with TUI-equivalent capture,
guarded dangerous actions, packaging, documentation, and tests.

The user clarified these choices:

- HACS/manual native custom integration first.
- Control mode is selected per device/config entry: monitor-only, temporary, or
  persistent.
- Profile capture initially uses the exact TUI source semantics: persistent
  `desired` state relative to `last_profile`, not a live-device snapshot.
- Home Assistant owns its profile catalogue; it does not directly share the
  CLI/TUI profile directory.
- All supported datapoints can have definitions, but defaults are curated.
  Dangerous communication settings and appliance reset are not ordinary
  control entities; guarded actions are used only where appropriate.
- Multiple devices and polling intervals configured in seconds are required in
  the first release.

My emphasis was control safety, persistence and reconciliation, write
confirmation and concurrency, profile selection/drift, HA-owned profile
storage and TUI-equivalent capture/lineage, names/overwrite/service UX,
import/export boundaries, and dangerous-action guards. I also evaluated the
complete lifecycle, entity/Recorder, packaging, and testing problem.

## Chain-of-Thought Summary

- Reuse the public controller/catalogue instead of rebuilding Modbus behavior,
  but add host-neutral persistence injection before the Home Assistant layer.
- Give each config entry exactly one runtime and one outer operation lock. Home
  Assistant schedules polling and reconciliation; the controller's background
  loops stay off.
- Treat persistent desired state and confirmed appliance state as different
  facts. The requested value is durable before I/O, but entity state remains
  the last confirmed read-back.
- Treat profile lineage, last requested profile, and current profile match as
  different facts. A profile select must never equate `last_profile` with a
  confirmed match.
- Preserve current capture behavior exactly at the semantic boundary while
  replacing filesystem persistence with Home Assistant storage.
- Make communication-setting changes out of scope for the initial write
  surface. Provide read-only diagnostics for those datapoints; expose appliance
  reset only through a strongly guarded administrator action.
- Build toward Home Assistant's current integration conventions: config-entry
  runtime data, a coordinator, explicit entity descriptions, stable IDs,
  translated action errors, unload/reload support, and clean dependency
  packaging.

## Findings grounded in the repository

### Reusable behavior and important limits

- [`src/wolf_325/__init__.py`](../../../src/wolf_325/__init__.py) is the declared
  stable facade. It exposes `WolfCWL2`, catalogue metadata, profile result
  types, value state, normalization, and typed failures. A Home Assistant
  integration should not import transport or TUI internals.
- The catalogue has 154 logical values: 44 fast, 90 slow, 18 static, and 2
  never-polled. It marks 78 writable, 69 restorable, 40 optional, 4 dangerous,
  and 2 one-shot definitions. This is the authoritative device schema, but it
  lacks Home Assistant platform/device-class/state-class/default-enabled
  semantics.
- [`src/wolf_325/settings.py`](../../../src/wolf_325/settings.py) already
  normalizes, cross-validates, persists desired state before I/O, writes
  activation-sensitive remote-control registers last, and reports partial
  results with `BulkWriteError`.
- [`src/wolf_325/writes.py`](../../../src/wolf_325/writes.py) performs read-back
  verification by default. Dangerous writes deliberately skip verification;
  unverified writes update the cache optimistically. Home Assistant must not
  generalize that latter behavior to ordinary control entities.
- [`src/wolf_325/transport.py`](../../../src/wolf_325/transport.py) serializes
  each Modbus request with `_io_lock`. It does **not** lock an entire bulk write,
  profile application, tier poll, or reconciliation. Those high-level
  operations can currently interleave at request boundaries.
- [`src/wolf_325/controller.py`](../../../src/wolf_325/controller.py) can run
  with `background=False`, which is the correct foundation for HA-owned
  scheduling. `start()` always attempts an initial all-tier poll, and
  `start(restore=True)` can apply desired state even after the initial poll
  failed. An HA wrapper must not restore until it has verified the connected
  serial number against the config entry.
- [`src/wolf_325/polling.py`](../../../src/wolf_325/polling.py) has three poll
  loops plus one reconcile loop. Enabling these alongside a Home Assistant
  coordinator would create two lifecycle owners. Its cached value callbacks do
  not fire on unchanged successful samples, although `updated_at` advances.
- A transport failure can leave values outside the failed block with old
  `available=True` values. The HA coordinator must impose device-level
  availability instead of copying per-value availability blindly.
- [`src/wolf_325/config.py`](../../../src/wolf_325/config.py) owns one JSON file
  that combines connection options, desired state, `last_profile`, profile
  path, and state-file path. That storage contract is unsuitable as the direct
  Home Assistant system of record. Some nominally async file operations also
  perform synchronous JSON/fsync work on the event loop.
- [`src/wolf_325/profiles.py`](../../../src/wolf_325/profiles.py) provides the
  right pure semantics but couples them to a filesystem directory. It supports
  inheritance, `replace`, `unset`, canonical validation, cycle/path guards,
  deterministic capture deltas, suffix-free safe names, explicit overwrite,
  and atomic replacement.
- Existing profile application is sequential, not device-atomic. A persistent
  application saves the desired bundle and `last_profile` before writes. A
  partial device failure can therefore leave lineage and desired state ahead of
  the confirmed appliance.
- Existing capture uses only persistent `desired` state and the `last_profile`
  parent. Temporary changes and live-but-unowned settings are excluded. Saving
  neither applies the new profile nor changes `desired` or `last_profile`.
- Current tests already prove the crucial behaviors: persistence before I/O,
  write ordering and verification, partial errors, restoration, read-only
  blocking, profile inheritance/capture lineage, optional-register isolation,
  and TUI confirmation phrases. See
  [`tests/test_controller.py`](../../../tests/test_controller.py),
  [`tests/test_profile_capture.py`](../../../tests/test_profile_capture.py),
  [`tests/test_transport_polling.py`](../../../tests/test_transport_polling.py),
  and [`tests/test_tui_service.py`](../../../tests/test_tui_service.py).

### Consequences that should be explicit in the plan

1. A persistent write can fail at the appliance yet remain durably queued. A
   service failure therefore does not mean “nothing changed.”
2. Temporary profile application writes resolved `settings`, but `unset` and
   `replace` are ownership directives and have no live-device effect when
   `persist=False`.
3. `last_profile` is lineage, not proof that the appliance matches the profile.
   Persistent manual edits deliberately keep this marker.
4. Device-level atomic profile application and rollback are unsupported.
   Compensation writes would introduce new failure modes and should not be
   implied.
5. The protocol has no compare-and-swap/revision primitive. Local operations
   can be serialized, but an external TUI, local panel, or second HA instance
   remains a last-writer race detectable only by later polling.

## Recommended implementable architecture

### Dependency and packaging boundary

Use two layers with a one-way dependency:

```text
custom_components/wolf_cwl2 (HA lifecycle, storage, entities, actions)
                         |
                         v
wolf_325 (transport, catalogue, validation, state, profile semantics)
                         |
                         v
              PyModbus / appliance gateway
```

Refactor the library without breaking `WolfCWL2(config_path=...)` for CLI/TUI:

- Add an in-memory/runtime constructor or factory that accepts normalized
  connection/polling/verification settings and injected persistence ports.
- Define host-neutral `DesiredStateRepository` and `ProfileRepository`
  protocols. Keep file-backed implementations as the defaults used by the
  current JSON/CLI/TUI entry points.
- Extract profile parsing/resolution/delta calculation from `ProfileLoader` so
  both file and HA repositories use one implementation. Do not duplicate
  profile validation in the custom component.
- Permit state-file persistence to remain disabled in the HA runtime. Recorder
  and diagnostics own HA history; a duplicate `wolf_state.json` has no clear
  HA purpose.
- Move Textual out of the core library's mandatory requirements (for example,
  into a `tui` extra). A HACS integration requirement should not install a TUI
  framework into Home Assistant.
- Publish and pin a `wolf-325` package release in `manifest.json`. Vendoring the
  client inside `custom_components` would work for an early prototype, but it
  creates two release streams and weakens the future Core path; it is not the
  preferred production design.

Suggested custom-component responsibility split, keeping every source file
under 300 lines:

```text
custom_components/wolf_cwl2/
  __init__.py              config-entry setup/unload only
  manifest.json            pinned library dependency and integration metadata
  config_flow.py           discovery/manual/reconfigure/options flows
  const.py                 shared constants and typed ConfigEntry alias
  runtime.py               per-entry runtime and operation state
  coordinator.py           tier deadlines, refresh, reconciliation owner
  storage.py               HA Store repository and schema migrations
  profile_service.py       HA-owned catalogue operations and sync evaluation
  services.py              action registration, target resolution, error mapping
  entity.py                common coordinator entity behavior
  descriptions/            complete HA semantic overlay split by responsibility
  sensor.py, binary_sensor.py, number.py, select.py, switch.py, button.py
  diagnostics.py
  strings.json, services.yaml, translations/en.json
hacs.json
```

The HA semantic overlay must classify every catalogue key exactly once or
explicitly mark it intentionally composite/action-only. Generate entity
instances from `REGISTERS` plus this overlay; do not copy wire addresses,
bounds, enum labels, scale, units, or dangerous/restorable flags into a second
schema.

### One runtime owner per config entry

Each config entry owns a typed runtime object in `entry.runtime_data`:

```text
WolfRuntime
  controller: WolfCWL2
  coordinator: WolfCoordinator
  store: HaWolfStore
  operation_lock: asyncio.Lock
  stopping: bool
  control_mode: monitor_only | temporary | persistent
  expected_serial: str
  profile_candidate: str | None
  desired_sync: DesiredSyncState
  profile_sync: ProfileSyncState
```

The lifecycle contract is:

1. Load the HA store and validate its profile catalogue without Modbus I/O.
2. Build the controller from config-entry data/options and injected HA
   repositories.
3. Start the controller with background loops disabled and restoration
   disabled.
4. Perform one coordinator-owned initial poll, including static identity.
5. Refuse writes and fail/retry setup until the returned serial number matches
   the config entry's unique ID. A host reconfigure must also prove the same
   serial unless a separate explicit “replace device” flow is designed.
6. In persistent mode only, reconcile stored desired state after identity is
   verified. Never restore to an unverified endpoint.
7. Forward entity platforms. The coordinator is thereafter the only periodic
   poll/reconcile scheduler.
8. On unload, reject new operations, let an active high-level operation finish
   within a documented bound, cancel scheduled work, then call
   `controller.stop()`. Do not cancel a profile halfway between register writes
   merely because platforms are unloading.

Multiple config entries get independent controller/client/lock/store state.
The config flow reads the device serial and uses it as `ConfigEntry.unique_id`,
rejecting duplicate setup. Entity unique IDs are derived from the immutable
serial plus canonical function key, never host, config-entry title, or current
profile name.

### Polling and entity publication

- Use one `DataUpdateCoordinator` per entry. Run it at the configured fast
  cadence and select due tiers using monotonic deadlines; slow and static tiers
  need not be integer multiples of fast. The underlying call is
  `controller.poll_once(tiers=due)` under `operation_lock`.
- Enforce safe option bounds in seconds. Home Assistant currently documents a
  5-second minimum polling interval; use at least 5 seconds for fast polling
  and validate slow/static/reconcile relationships rather than silently
  correcting them.
- Reconciliation is another due operation performed by the same coordinator
  owner under the same lock. Do not call `controller.start(background=True)`.
- After a successful write, explicitly refresh the affected definition(s)
  before publishing entity state. A bulk/profile action refreshes all attempted
  keys after completion, including keys whose write failed if communication is
  still possible.
- A coordinator transport failure marks the device unavailable as a whole.
  Old per-register `available=True` cache entries must not remain available in
  HA. An isolated optional/unsupported datapoint on an otherwise successful
  update should publish `unknown` (or be omitted when capability detection is
  conclusive), rather than making the whole device unavailable.
- Entities read memory only. They do not call `refresh()` from value properties.
- Construct coordinator data without volatile `generated_at` or raw-word
  attributes in equality/history paths. Raw words, errors, timestamps, and
  connection generations belong in redacted diagnostics, not frequently
  changing Recorder attributes.

### Stable entities and Recorder semantics

- Use a curated enabled-by-default set based initially on the 19 proven
  `OVERVIEW_KEYS`, plus a deliberately reviewed small set of maintenance and
  identity/profile-health entities. Mark optional, static identity,
  installation, fast-changing diagnostic, and advanced controls disabled by
  default as appropriate.
- Define all supported datapoints through the semantic overlay. Safe writable
  booleans/enums/numbers map to switch/select/number entities. Read-only values
  map to sensor/binary-sensor platforms. Filter reset maps to a button.
  Dangerous communication values map only to read-only, disabled-by-default
  diagnostic sensors in release one. Appliance reset has no ordinary entity.
- Give every entity `has_entity_name=True`, device info, translation keys,
  entity category, and a stable unique ID. Firmware/hardware/serial belong in
  device info or diagnostic entities, not repeated attributes.
- Assign sensor device classes, native units, display precision, and state
  classes explicitly. Instantaneous temperature, humidity, pressure, airflow,
  voltage, RPM, and CO2 values are measurement candidates. Do not label a
  counter `TOTAL` or `TOTAL_INCREASING` without proving its reset and monotonic
  behavior. Settings/setpoints get no state class.
- Unknown future enum values already decode as `unknown_<raw>`. Read-only enum
  sensors must tolerate that value without corrupting a fixed options contract;
  writable selects retain only known writable options and publish no current
  option when the appliance returns an unknown value.
- Entity state is always confirmed cached appliance state. Pending desired
  state is exposed separately, never by making a number/select optimistically
  show an unconfirmed request.

## Proposed control contracts and workflows

### Per-entry mode matrix

| Behavior | Monitor-only | Temporary | Persistent |
|---|---:|---:|---:|
| Poll and record | yes | yes | yes |
| Safe entity writes | reject | `persist=False` | `persist=True` |
| Safe profile apply | reject | write resolved settings only | persist ownership, then write |
| Startup/reconnect restore | no | no | yes, after serial verification |
| Periodic enforcement | no | no | yes |
| Existing desired state | retained but dormant | retained but dormant | active |
| Release desired ownership | allow only through an explicit local-state admin action | allow | allow |
| TUI-equivalent capture | reject to preserve strict read-only semantics | allowed only if a nonempty dormant desired delta exists; temporary writes remain excluded | allowed |
| Filter reset | reject | allow | allow; never persisted |
| Dangerous admin action | reject | allow if fully guarded | allow if fully guarded; always temporary |

The one nuance worth resolving explicitly in the final plan is local profile
management during monitor-only operation. Current TUI `--read-only` blocks
profile capture as well as device writes, so the table preserves that behavior.
Import/export could remain available as separate administrator storage actions
because they do not capture or control the device, but this must be documented
as catalogue management rather than appliance control.

Mode changes must not silently discard desired state. Persistent to temporary
or monitor-only leaves desired state and lineage dormant. When changing back to
persistent with a nonempty desired mapping, the options flow must present the
exact stored values and require an explicit choice to resume/apply them or clear
ownership; there should be no implicit fallback. Stop reconciliation before
changing away from persistent mode.

### Confirmed single-setting write

Every ordinary entity mutation follows this sequence:

1. Resolve the config entry and reject if unloading or monitor-only.
2. Acquire the per-entry `operation_lock`.
3. Recheck mode/availability after acquiring the lock.
4. Normalize and cross-validate through the public library/catalogue.
5. In persistent mode, durably commit the desired value before I/O. In
   temporary mode, do not modify desired state or lineage.
6. Call the verified controller write. Do not update the HA entity
   optimistically.
7. Refresh/read back the target and publish the confirmed value.
8. On validation misuse, raise a translated `ServiceValidationError`. On
   communication/verification failure, raise a translated `HomeAssistantError`
   that states whether persistent desired state remains queued.
9. Release the operation lock and request a coordinator publication.

Invariants:

- At most one high-level poll, reconcile, write, profile operation, capture, or
  dangerous action executes per entry at a time.
- The outer lock is always acquired before the controller's internal I/O lock;
  no code obtains them in reverse order.
- Successful entity completion means the appliance read-back matched under the
  catalogue tolerance. It does not mean no external writer can change it one
  millisecond later.
- Validation failure changes neither HA storage nor the appliance.
- Temporary write failure leaves no queued desired change.
- Persistent write failure may leave a queued desired change; confirmed entity
  state remains actual/unknown, not requested.

Do not coalesce commands during release one. Serialize them in accepted order
so every caller receives a truthful result. A later target request naturally
runs after an earlier one. This is easier to reason about than silently dropping
commands from automations.

### Reconciliation and desired drift

Track desired convergence separately from entity state:

```text
inactive     no active persistent authority in this mode
synced       every desired key is available and equals confirmed state
pending      offline, just persisted, reconnecting, or not yet confirmed
drifted      confirmed current value differs; reconciliation is eligible
suspended    repeated verification/validation failures require intervention
```

Recommended entities are an enabled-by-default binary sensor such as “Desired
state synchronized” in persistent mode and a disabled-by-default diagnostic
sensor with the richer status/pending-key count. Do not put the whole desired
mapping or per-key errors in Recorder attributes; diagnostics and action
responses can carry details.

The current controller will retry persistent mismatches indefinitely. Add a
bounded per-key retry/backoff policy in the HA owner: transport outages back
off and recover automatically, while repeated verification mismatch for the
same value eventually suspends that key and creates an actionable repair issue.
A new value, explicit apply-desired action, or confirmed device recovery clears
the suspension. This avoids writing a setting every reconcile interval forever.

### Bulk/profile application

- Acquire the outer lock for the entire resolve, persistence, ordered write,
  and final refresh sequence. This closes the current local interleaving gap.
- Preflight the fully resolved profile and the candidate desired mapping before
  any persistence or device write.
- Persistent mode commits `desired` and `last_profile` as one HA Store revision
  before I/O, preserving the repository's current safety contract.
- Temporary mode writes only resolved `settings`. `replace` and `unset` do not
  reset live values and do not mutate ownership.
- Use the controller's deterministic safe write order. There is no appliance
  transaction and no rollback.
- On partial failure, return/report successful keys and failed/not-attempted
  keys. In persistent mode, failed targets remain pending for reconciliation.
  In temporary mode, successful values stay applied and failures require a new
  explicit request.
- A select entity cannot return a detailed result, so it must raise a translated
  action error on any partial failure and profile-health entities must update.
  A domain action `apply_profile` may additionally support a response mapping
  for automation authors.

## Profile storage, capture, selection, and drift

### Home Assistant-owned store

Use `homeassistant.helpers.storage.Store`, preferably one isolated key per
config entry. Connection/poll options remain in `ConfigEntry.data/options`; the
store contains device-owned control records:

```json
{
  "schema_version": 1,
  "revision": 7,
  "desired": {"remote_control_mode": "level"},
  "last_profile": "night",
  "profiles": {
    "night": {
      "description": "Quiet overnight operation",
      "replace": false,
      "settings": {"remote_ventilation_level": "low"},
      "unset": []
    }
  }
}
```

The outer Home Assistant storage schema version/revision is distinct from the
portable profile-document schema. Desired and `last_profile` must be committed
in one awaited durable save before a persistent write. Delayed saves are not
acceptable for this safety invariant. Store mutations are protected by the
same entry operation lock.

Profiles are scoped to one config entry/device in release one. This avoids
silently applying settings across capability/firmware differences and makes
entry removal/backup ownership clear. Cross-device reuse occurs only through
explicit import/export.

### Exact initial capture contract

`capture_profile` must preserve the existing workflow:

- Source is canonical, durable `desired`, never live/cached registers.
- Parent is exactly `last_profile` when non-null; it is not inferred from a
  matching profile or last temporary apply.
- A parented capture stores only sorted changed/new `settings` and sorted
  inherited keys absent from desired under `unset`; it copies the resolved
  parent's `replace` flag.
- A standalone capture stores the full desired mapping, empty `unset`, and
  `replace=false`.
- Temporary writes/profile applies are absent.
- Reject invalid/non-restorable state, missing/cyclic parent, self-extension,
  empty delta, unsafe name, and collision without explicit overwrite.
- Success saves one document only. It does not apply/select it and does not
  change `desired` or `last_profile`.

Keep the current name contract exactly: `[A-Za-z0-9_.-]+`, no `.json` suffix,
case preserved. Name is the durable profile identifier; description is display
text. Do not use descriptions as select options or inheritance identifiers.

### Service/action UX for capture and overwrite

Register actions once at integration setup, with a device/config-entry target
resolver so multi-device calls cannot be ambiguous:

- `preview_profile_capture` (read-only response): returns store `revision`,
  base, replace, settings, unset, and `has_changes`.
- `capture_profile` (administrator mutation): target, required `name`, optional
  `description`, `overwrite=false`, and optional `expected_revision`. It returns
  the exact saved delta and new revision.
- `apply_profile` (optional response action): target, name, and mode-constrained
  persistence behavior; entity selection remains the normal UI.

`overwrite` must default false and be explicit. If `expected_revision` is
provided, reject a stale preview rather than saving a different delta. Even
without a prior preview, `capture_profile` computes and returns the exact delta
that it saved atomically. After save/overwrite/import, update the profile select
options through the runtime dispatcher/coordinator without reloading the entry.

Before an overwrite commits, resolve and validate the complete resulting
catalogue, including descendants, so an overwritten parent cannot leave stored
children cyclic or invalid. This is an additional HA repository integrity
guard; the actual captured document and lineage semantics remain TUI-equivalent.

### Profile selection versus profile match

Keep three facts separate:

| Fact | Source | Meaning |
|---|---|---|
| lineage base | persisted `last_profile` | parent for later capture |
| candidate | last applied name in runtime, or persisted lineage after restart | profile whose match is being evaluated |
| confirmed match | current confirmed values versus candidate's fully resolved settings | whether target keys now match |

The profile select options are a reserved localized “No confirmed profile”
sentinel plus current profile names. Selecting a name starts an apply. Its state
becomes that name only after all resolved profile settings have confirmed
read-backs; otherwise it returns to the sentinel. Do not automatically choose an
arbitrary profile merely because multiple partial profiles happen to match.

Expose lineage as a separate disabled-by-default diagnostic sensor. Expose
profile sync as `matched`, `pending`, `drifted`, `partial_failure`, or
`unavailable`. Inherited `unset` values are ownership releases with no expected
live value, so they are excluded from live-match comparison. Unrelated desired
settings retained by a merge profile also do not make the selected profile
drift.

After external/local-panel changes are polled, a mismatch in a candidate
profile setting changes the select to the sentinel and status to drifted.
Persistent mode may subsequently reconcile it; temporary mode observes and
leaves the drift. A temporary applied candidate is runtime-only and is not
claimed after a Home Assistant restart.

### Import/export boundary

Do not read or watch the CLI/TUI profile directory and do not point two
processes at one file store. That would reintroduce stale reads and cross-process
last-writer races.

Define an explicit portable envelope for a later first-party action pair:

```json
{
  "format": "wolf-cwl2-profile-bundle",
  "schema_version": 1,
  "profiles": {"name": {"description": "...", "settings": {}, "unset": []}}
}
```

- Export returns portable profile documents, not filesystem paths, HA entry
  IDs, desired state, serial numbers, or credentials.
- Import accepts an object/bundle, validates names, inheritance, all setting
  values, cross-setting constraints, cycles, and missing parents before one
  store commit. Collision policy defaults to reject; overwrite is explicit.
- Single-child imports with an absent parent fail unless the parent already
  exists. Bundle validation can resolve parents within the same bundle.
- Desired state and `last_profile` are not profile export data. A separate HA
  backup/restore owns the complete Store document.
- The current TUI JSON document is directly representable inside the bundle,
  preserving a clean manual interchange path without shared storage.

If scope must be reduced, implement and test the repository interface and
portable schema in release one, but defer user-facing import/export actions.
Do not implement an undocumented filesystem shortcut.

## Dangerous and one-shot operations

The exact catalogue cases are:

- non-restorable date/time writes: four safe-but-temporary register values;
- dangerous communication writes: `modbus_interface_type`,
  `modbus_slave_address`, and `modbus_speed`;
- one-shot normal action: `filter_reset_status`;
- one-shot dangerous action: `appliance_reset_status`.

Recommended release-one policy:

1. Show the three communication datapoints only as disabled-by-default
   read-only diagnostic sensors. Do not expose a generic dangerous-register
   write service. Changing them can sever the active session, controller
   verification is intentionally skipped, and config-entry connection settings
   may become wrong.
2. Expose filter reset as a normal button in temporary/persistent modes. It is
   never desired state. Refresh its status after the command where possible.
3. Expose appliance reset only as an administrator action, never a button. It
   requires all of: one unambiguous device target, exact case-sensitive
   `RESET APPLIANCE`, the expected device serial repeated by the caller, a live
   serial match, and a user-originated administrator context. Reject automation
   or script contexts if the product decision is “interactive guard only.”
4. Appliance-reset success means only “command dispatched.” Mark the
   coordinator unavailable, close the stale connection (the controller already
   does this), and enter normal reconnect backoff. Never claim the physical
   reset completed.
5. Dangerous operations always bypass persistence regardless of control mode.
   Monitor-only rejects them.

A later communication-reconfiguration workflow should be a dedicated wizard,
not `write_register(name, value)`. It needs to capture old and new connection
parameters, warn about the gateway recovery path, perform the temporary write,
update/reconfigure the entry when possible, and create a repair issue on lost
contact. That is substantially larger than an ordinary number/select entity
and should not block safe release-one monitoring/control.

## Failure semantics

| Failure | Durable desired state | Entity state | User-visible result |
|---|---|---|---|
| Preflight validation | unchanged | unchanged | translated validation error |
| Temporary transport failure | unchanged | unavailable/last confirmed cache | action failure, no retry ownership |
| Persistent transport failure after save | requested value queued | unavailable/last confirmed, never requested | failure explicitly says queued/pending |
| Verification mismatch | requested value queued only in persistent mode | actual read-back | verification error; bounded reconciliation/repair |
| Partial persistent profile | full intended ownership and lineage saved | per-key confirmed results | partial error plus pending failed keys |
| Partial temporary profile | unchanged | successful keys stay applied | partial error; no rollback or automatic retry |
| External writer drift | unchanged | new confirmed external value | drift status; persistent mode later reasserts |
| Missing/corrupt profile parent | desired control remains loaded | device monitoring continues | profile features blocked and repair issued |
| Entry unload during operation | no new operation accepted | final confirmed snapshot | active operation drains within bound, then transport stops |

HA error translation should retain typed distinctions from `WolfError` rather
than expose Python exception text indiscriminately. Diagnostic downloads should
redact host and serial consistently and never include credentials (none exist in
the current protocol, but the boundary should be future-safe).

## Phase implications for an implementation plan

### Phase 0 — contracts and library seams

- Add tests first for repository injection, in-memory controller construction,
  profile pure resolution/capture, disabled state-file behavior, and unchanged
  file-backed CLI/TUI compatibility.
- Introduce desired/profile repository protocols and HA-safe runtime config.
- Move Textual to an optional TUI dependency and prepare a publishable core
  package with license/project metadata.
- Update `.docs/ARCHITECTURE.md`, `.docs/code-relationships.md`, the controller
  API/JSON contract, profile-capture workflow, and a new HA runtime/storage
  contract. Record the one-owner/one-lock decision in a durable decision entry.

### Phase 1 — native integration, multi-entry monitoring, and Recorder surface

- Scaffold `custom_components/wolf_cwl2`, manifest, HACS metadata,
  translations, config/reconfigure/options flows, and runtime data.
- Probe identity and prevent duplicate serial entries.
- Implement one coordinator with due tiers, option bounds in seconds,
  setup/unload/reload, device availability, and diagnostics.
- Build the complete semantic entity overlay and curated defaults. Land
  read-only sensor/binary-sensor entities first and verify stable unique IDs and
  Recorder metadata.

### Phase 2 — safe controls and desired-state reconciliation

- Add the per-entry operation owner/lock and translated domain-error mapping.
- Add safe number/select/switch entities and filter-reset button under the mode
  matrix.
- Add HA Store desired/lineage migration, confirmed write publication,
  reconnect restore after serial verification, desired sync state, bounded
  reconciliation, and mode-transition UX.
- Add profile apply through the select and optional response action, including
  partial-failure and drift behavior.

### Phase 3 — HA-owned profile capture and management

- Add in-memory HA profile repository, full-catalogue validation, dynamic select
  option refresh, preview/capture actions, explicit overwrite/revision checks,
  and exact capture lineage tests.
- Add portable bundle import/export if retained in first-release scope;
  otherwise document the versioned boundary and defer only the service surface.

### Phase 4 — guarded administration and release hardening

- Add guarded appliance-reset administrator action and reconnect behavior.
- Add repairs, redacted diagnostics, user/HACS documentation, examples,
  manifest/HACS validation, release automation, and a clean-install smoke test.
- Leave communication writes read-only until a dedicated reconfiguration design
  is implemented and physically tested with an explicit recovery plan.

## Validation implications

Follow repository TDD: write behavior tests before each implementation slice,
mocking only the external Modbus/Home Assistant host boundaries, not source
logic.

### Library tests

- File and in-memory repositories resolve identical inheritance/replace/unset
  results and reject the same malformed values.
- Desired plus `last_profile` is one atomic repository commit before the first
  write attempt.
- Capture round-trips to the exact desired mapping and does not read Modbus.
- Capture names, `.json` suffix, self-parent, cycles, missing parents, empty
  deltas, deterministic ordering, collisions, overwrite, and descendant
  validation.
- Existing CLI/TUI profile and controller tests remain unchanged and passing.

### Home Assistant lifecycle/multi-device tests

- Config flow tests connection, captures serial, prevents duplicates, and
  rejects a reconfigured endpoint with a different serial.
- Two config entries create independent devices, IDs, stores, controllers,
  schedules, locks, profile catalogues, and unload paths.
- Exactly one polling owner exists; controller background/reconcile tasks are
  absent.
- Fast/slow/static due-tier scheduling and second-based option changes are
  deterministic under a fake clock.
- Initial/offline setup, recovery, unload, reload, and removal clean up tasks
  and transport.

### Entity/Recorder tests

- Every catalogue definition is classified exactly once; all dangerous writes
  are absent from normal control platforms.
- Curated default enabled flags are snapshot-tested independently from the
  catalogue's wire metadata.
- Unique IDs and device identifiers remain stable across host, title, polling,
  mode, and profile changes.
- Every numeric sensor's unit/device class/state class combination is legal.
  Counters with unproven semantics have no statistics class.
- No raw words, generated timestamps, errors, or full desired/profile mappings
  appear as frequently recorded attributes.
- Device transport loss makes all entities unavailable; isolated optional data
  becomes unknown without taking down healthy entities.

### Control/concurrency tests

- Matrix tests cover every mode and operation category.
- Entity state stays at confirmed current value while a write is pending and
  after verification failure.
- Offline temporary write leaves storage unchanged; offline persistent write
  is durably pending and reports that fact.
- A blocking fake gateway proves no poll, second entity write, reconcile, or
  profile apply interleaves inside a high-level bulk operation.
- Concurrent requests serialize deterministically; unload waits for or safely
  terminates the active owner without starting another request.
- Activation-sensitive remote mode remains last; partial results/not-attempted
  keys propagate through translated HA failures.
- Reconciliation restores only after live serial verification, detects
  external drift, backs off, suspends repeated mismatch, and clears suspension
  only through a defined event.

### Profile tests

- Persistent and temporary profile application differ exactly as specified;
  `replace`/`unset` have no live clearing meaning in temporary mode.
- `last_profile` persists through persistent edits/releases while profile match
  correctly becomes drifted when a profile-owned setting differs.
- The select changes to the profile only after complete confirmation, returns
  to the sentinel on external drift/partial failure, and never infers among
  multiple matching partial profiles.
- Temporary candidate is lost on restart; persistent lineage survives.
- Capture excludes temporary writes, uses dormant desired state when permitted,
  rejects an empty delta, does not select/apply the saved profile, and refreshes
  options without entry reload.
- Preview revision protects against stale save when requested.
- Import/export bundle validation is all-or-nothing and round-trips current TUI
  profile documents without HA identifiers or secrets.

### Dangerous-operation and packaging tests

- Communication settings and appliance reset have no normal control entities.
- Filter reset is mode-gated and never persisted.
- Appliance reset rejects non-admin, ambiguous target, wrong phrase, wrong
  serial, monitor-only, and automation context; accepted dispatch reports only
  `command_sent` and starts unavailable/reconnect behavior.
- A clean Home Assistant install loads the pinned library without Textual.
- Validate `manifest.json`, translations, service schemas, HACS metadata,
  diagnostics redaction, and package import against the supported HA version
  range.

Physical tests remain read-only by default. Any live write/profile/reset test
requires the existing physical-device workflow's explicit target and restore
value; appliance and communication resets require a separate recovery plan.

## Risks and tradeoffs

- **Library refactor versus generated JSON config:** injecting repositories is
  more initial work, but generating controller config/profile files inside HA
  would make two systems of record, invite event-loop file I/O, and weaken Core
  compatibility.
- **Coordinator-owned versus controller-owned polling:** coordinator ownership
  needs due-tier logic, but it gives Home Assistant one lifecycle/error owner
  and permits one outer lock. Controller background loops would make HA unload,
  availability, and request sequencing harder to prove.
- **Confirmed UI versus responsiveness:** confirmed writes take at least the
  verification delay/read. This is slower than optimistic state but avoids
  misrepresenting failed or normalized appliance state.
- **Persistent control authority:** it intentionally overrides local-panel or
  third-party drift. The mode label, options warning, sync entity, and dormant
  desired behavior must make that authority visible.
- **No device transaction:** a profile can partially apply. Persistent mode
  offers eventual convergence; temporary mode cannot. Pretending rollback is
  atomic would be more dangerous than reporting partial truth.
- **Profile select sentinel:** it is less visually simple than echoing
  `last_profile`, but it preserves truthful current-state semantics and Recorder
  history.
- **Per-device profiles:** this duplicates catalogues when several identical
  appliances share profiles. It is safer initially; explicit portable export /
  import is the controlled sharing boundary.
- **No release-one communication writes:** this narrows “all controls,” but all
  three values remain monitorable and the omission follows the clarified
  dangerous-operation policy. A proper reconfiguration wizard can be added
  without destabilizing ordinary entities.
- **Published dependency:** pinning a small core library is the cleanest HACS
  and Core path, but requires release/version discipline and checking PyModbus
  compatibility with supported Home Assistant environments.

## System-of-record updates implied by implementation

Implementation should update the owning records rather than append a generic
completion note:

- `.docs/ARCHITECTURE.md`: HA layer, dependency direction, per-entry lifecycle,
  and storage boundary.
- `.docs/code-relationships.md`: platforms, description overlay, coordinator,
  store, actions, and their test owners.
- `.docs/contracts/controller-api-and-json.md`: injected runtime/repository API
  while preserving file-backed compatibility.
- `.docs/contracts/home-assistant-integration.md` (new): config entries,
  identity, entity IDs, modes, actions, availability, Recorder, and error
  contracts.
- `.docs/contracts/home-assistant-storage.md` (new): Store version, atomic
  desired/lineage commit, profile document/envelope, and migrations.
- `.docs/workflows/profile-capture.md`: add the HA-owned repository/action path
  while keeping capture semantics identical.
- `.docs/workflows/home-assistant-operation.md` (new): setup, modes, restores,
  profile drift, dangerous guards, diagnostics, unload/removal, and recovery.
- `.docs/decisions/*` (new): one HA polling/operation owner; HA-owned per-entry
  profile storage; dangerous communication writes deferred.

## Current Home Assistant references consulted

- [Fetching data / DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Entity contract and registry metadata](https://developers.home-assistant.io/docs/core/entity/)
- [Sensor and long-term statistics semantics](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [Integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Integration Quality Scale rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/)
- [Action failure semantics](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/action-exceptions/)
- [Permissions and administrator services](https://developers.home-assistant.io/docs/auth_permissions/)
