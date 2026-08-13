# Agent 3 — Home Assistant delivery, packaging, and verification

## Source Task

Design an implementation-plan-ready native Home Assistant custom integration
for the public `wolf_325.WolfCWL2` API. The first distribution target is
HACS/manual installation, while keeping a credible path to Home Assistant Core.
The first release must support multiple appliances/config entries, one polling
and lifecycle owner per appliance, stable Recorder-safe entities, per-entry
monitor-only/temporary/persistent control modes, a curated default surface with
all supported datapoints defined, Home Assistant-owned profiles with exact TUI
capture semantics, and guarded dangerous actions. This is analysis only; no
implementation is authorized in this pass.

The clarified choices are binding:

- HACS/manual native custom integration, not an add-on or external bridge.
- One control mode per config entry: monitor-only, temporary, or persistent.
- Profile capture means persistent `desired` delta versus `last_profile`, not a
  live register snapshot.
- Home Assistant owns its profile persistence; it does not share profile files
  with the CLI/TUI in release one.
- Every supported datapoint has an explicit HA representation or explicit
  action-only exclusion, but only a curated subset is enabled by default.
- Dangerous communication/reset controls are not ordinary control entities.
- Multiple devices and polling intervals in seconds are release-one features.

## Chain-of-Thought Summary

- The current controller is reusable, but its constructor and profile behavior
  are coupled to filesystem JSON and its distribution unconditionally installs
  Textual. A small public persistence/configuration seam and a lightweight
  published client package are prerequisites for a clean HACS integration and
  future Core submission.
- Home Assistant should own scheduling. Each config entry owns exactly one
  controller, coordinator, operation lock, and HA storage instance; the
  controller runs with `background=False`. This prevents controller loops,
  entity polling, writes, and reconciliation from racing each other.
- Entity identity and Recorder meaning must be designed explicitly. Modbus type
  metadata is not sufficient to infer device class, state class, unit,
  platform, default enablement, or exclusion policy.
- The HA test harness should exercise the real integration through config
  entries, entity state, services/actions, registries, and HA storage while
  replacing only the external Modbus client. Each implementation slice starts
  with its behavior tests.
- Physical validation remains read-only by default. No reset, communication
  write, profile apply, or persistent ownership test is implicitly authorized.

## Findings

### Required architecture

Use the immutable integration domain `wolf_cwl2`. A config entry represents one
physical appliance/unit, not the entire repository and not an arbitrary set of
gateways. Its `unique_id` is the successfully read 12-digit
`serial_number`; host, port, and Modbus unit ID are mutable connection data.
Device identifiers are `{(DOMAIN, serial)}` and entity unique IDs are
`<serial>:<semantic-key>`, never host-, entry-ID-, or entity-name-based. Setup
must not invent a fallback identity if the required serial cannot be read.

Each loaded entry owns a typed runtime bundle:

```text
ConfigEntry
  -> WolfCWL2Runtime (only operation/lifecycle owner)
       -> WolfCWL2(background=False)
       -> WolfCWL2Coordinator (only poll scheduler/fan-out owner)
       -> asyncio.Lock (covers a whole poll/write/profile/reconcile operation)
       -> HomeAssistantControllerStore (desired + last_profile)
       -> HomeAssistantProfileStore (profile documents)
```

`async_setup_entry` loads the HA stores, starts the controller once with no
background tasks, accepts the initial all-tier snapshot as coordinator data,
and then forwards platforms. If initial setup fails after allocating a client,
it must stop the controller before raising `ConfigEntryNotReady` or a permanent
setup error. `async_unload_entry` unloads platforms, cancels coordinator work,
and awaits controller shutdown. Unloading one entry cannot touch another.
`async_remove_entry` deletes only that entry's HA-owned storage.

The coordinator ticks at the configured fast interval and calculates which of
`fast`, `slow`, and `static` are due from monotonic deadlines. One call to
`controller.poll_once(tiers=due)` completes before it publishes one immutable
snapshot. Persistent reconciliation is another due operation performed behind
the same lock; it never gets a second loop. Entity `should_poll` is false and
platforms do not call `refresh()` independently. The runtime lock must cover
complete bulk/profile operations because the controller's `_io_lock` only
serializes individual Modbus requests.

Coordinator data should compare meaningful state only: decoded value,
availability, connection success, desired ownership, profile lineage, and
profile catalogue. Exclude sample timestamps, raw words, and generated-at from
equality so unchanged samples do not create needless HA state writes. Keep
timestamps and categorized errors in a separate diagnostics view. Entity
availability is `coordinator.last_update_success AND controller.connected AND
value.available`; this prevents later blocks retaining apparently current
values after a transport failure. Optional unsupported values become
individually unavailable without taking down the entry.

### Client-library seam and dependency isolation

Do not make the integration synthesize a `wolf_cwl2_config.json` under
`.storage`, and do not copy the current library into `custom_components`.
Instead, preserve `WolfCWL2(config_path=...)` for CLI/TUI users and add a public
HA-neutral construction path such as `WolfCWL2.from_config(config,
controller_store, profile_store)`. Define async protocols for mutable
desired/lineage state and profile-document list/load/save. Refactor the existing
filesystem behavior into protocol adapters; extract profile resolution/capture
into store-independent logic. HA implementations of those protocols live only
in the custom integration and use `homeassistant.helpers.storage.Store`.

This seam also fixes an existing HA blocker: `atomic_json_write()` and
`read_json()` currently execute filesystem work on the event-loop thread.
Filesystem adapters must use `asyncio.to_thread`; HA adapters use HA's async
storage helper. Add a public one-shot reconciliation method if necessary so the
HA runtime does not duplicate `_reconcile_loop`'s connection-generation rules.
Record the new surface in
`.docs/contracts/controller-api-and-json.md` without exposing controller
internals.

Make `wolf-325` a lightweight publishable dependency with only PyModbus in its
base requirements. Move `textual>=8.2,<9` to a `tui` optional dependency and
keep TUI tests in the corresponding development group. Publish the client
before releasing a component whose `manifest.json` pins
`wolf-325==<released-version>`. This avoids HACS copying files outside
`custom_components/wolf_cwl2` and preserves the normal future-Core external
library boundary. A build/clean-import test must prove importing `wolf_325` and
constructing its controller does not import or require Textual.

This repository currently has no Git remote, license metadata, project URLs, or
identified GitHub code owner. Those are release blockers, not values the plan
should invent. They must be resolved before completing `manifest.json`, PyPI
metadata, HACS publication, Brands registration, or issue/documentation URLs.

### Control-mode contract

- **Monitor-only:** polling and profile listing remain available. Every write,
  release, apply, capture, reconcile, and reset entry point rejects before
  persistence or device I/O. State-bearing setting entities retain stable
  identities, but calls to their write methods fail with a translated
  monitor-only error; HA has no native read-only form of `NumberEntity`,
  `SelectEntity`, or `SwitchEntity` that also preserves its entity/history.
- **Temporary:** safe entity writes and profile application call the controller
  with `persist=False`. They do not change `desired` or `last_profile`, are not
  restored/reconciled, and remain excluded from capture. Profile capture must
  reject in this mode rather than silently saving historical desired state.
- **Persistent:** safe entity writes and profile applications use
  `persist=True`; desired state is saved before I/O, restored at startup/new
  connection, and reconciled at the configured seconds interval. An offline
  failure may therefore leave a queued desired value while the entity continues
  to show the last confirmed device value.

Changing mode or polling options reloads only that entry. Prefer
`OptionsFlowWithReload`; do not also install an update listener that causes a
second reload. Preserve desired/profile storage when moving away from
persistent mode, but make it inactive and expose its presence in diagnostics.

### Entity and Recorder contract

Add a HA-semantic catalogue keyed by canonical register name. It contains only
HA facts: platform, device/state class, native unit, entity category,
translation key, icon where justified, precision, default enablement, and any
composite/action-only classification. It must not duplicate addresses, codecs,
bounds, enums, writability, or safety flags from
`src/wolf_325/register_catalogue.json`.

A validation test must account for all 154 definitions exactly once as either
an entity-backed value, part of an explicitly documented composite, or one of
the two action-only reset registers. It must also prove every HA mapping points
to a real catalogue key and that dangerous communication registers never
produce writable entities. The initial default-enabled set should start from
the 19 `OVERVIEW_KEYS` in `src/wolf_325/tui_views.py`, plus a deliberately
reviewed small set of ordinary controls; identity, optional extension,
installer, static, and diagnostic values default disabled. Registry defaults
are immutable after first creation, so changes require release notes rather
than assuming existing installs update automatically.

Use `SensorStateClass.MEASUREMENT` only for supported instantaneous
measurements. Use `TOTAL`/`TOTAL_INCREASING` only for individually reviewed
counters whose reset/monotonic behavior is known; never infer it from `u32`.
Settings/setpoints and enum status values have no statistics state class. Map
units to HA canonical constants and use native values, not formatted strings.
Do not expose raw words, poll timestamps, connection errors, desired mappings,
or volatile debug information as ordinary state attributes. Unknown future
enum values remain observable on reads, but writes accept only documented
options. Tests must lock down this behavior for sensor and select entities.

Normal writable booleans/enums/numerics map to switch/select/number entities
with bounds and choices derived from `RegisterDef`; entities delegate writes to
the runtime and never call transport methods. Packed clock/date values need an
explicit reviewed mapping (native date/time composites or documented text
controls), not numeric inference. The profile select is synthetic: it lists the
entry's HA-owned profiles and applies one through the runtime. Its state means
"last applied/lineage", never "the appliance currently matches this profile";
partial apply, manual drift, normalization, and external writers make a match
claim false. Capture refreshes profile options immediately.

### Profiles and guarded actions

Store one versioned HA payload per entry, with normalized `desired`, optional
`last_profile`, and profile documents. Preserve the existing name, inheritance,
`replace`, `unset`, cycle/path-equivalent, collision, cross-setting, and atomic
save contracts. Capture is enabled only in persistent mode and uses stored
desired ownership versus resolved `last_profile`; it performs no device read,
does not apply/select the new profile, and requires a nonempty delta and
explicit overwrite.

Register domain-level HA actions once and resolve their required device target
to one loaded config entry:

- `capture_profile`: required device target and name; optional description and
  explicit `overwrite` (default false).
- `reset_filter_warning`: control-enabled modes only and exact confirmation
  phrase `EXECUTE ACTION`.
- `reset_appliance`: control-enabled modes only and exact confirmation phrase
  `RESET APPLIANCE`; call `reset_appliance(confirm=True)` and expect disconnect.

Do not expose the three dangerous Modbus communication writes in release one.
They may remain readable diagnostic entities but have no entity write method or
generic service escape hatch. All action handlers enforce mode and confirmation
server-side; `services.yaml` UI fields are not safety boundaries. Partial
profile writes must retain the existing `BulkWriteError` results/errors,
publish the resulting confirmed snapshot, and report that persistent desired
state remains queued.

### Diagnostics, repairs, and redaction

`diagnostics.py` should return integration/client versions, non-sensitive
option values, poll/task health, connection generation, last successful tier
times, availability/error-category counts, and canonical unavailable keys.
Omit raw words and live values. Redact host/IP, serial, config-entry identifiers,
profile names/descriptions, and any exception text that may contain endpoints.
Use `async_redact_data` as a second layer, not as the only design. Add `caplog`
and diagnostics snapshot tests with sentinel secrets. The current client logs
host, port, and unit ID and embeds the endpoint in a connection error; change
the library to log "configured gateway" plus a generation and sanitize public
connection errors before the integration is considered redaction-safe.

Transient disconnects belong in coordinator availability and rate-limited logs,
not persistent Repairs issues. Create actionable issues for an endpoint that
now reports a different serial, corrupt/unmigratable HA profile storage, and an
unsupported config/storage schema. A reconfigure flow updates endpoint fields,
rechecks the same serial, updates the existing entry, and reloads it; it must
never create a second entry. Initial release has no legitimate predecessor HA
schema, so do not invent a fake data migration. Establish config-entry
`VERSION`/`MINOR_VERSION` and HA Store version 1, test current-version load and
forward-version rejection, and require a tested `async_migrate_entry`/Store
migration with every later schema bump.

## Proposed delivery and package structure

No Python source file may exceed 300 lines. Large declarative HA metadata is a
JSON data file and is validated behaviorally.

```text
src/wolf_325/
  config.py                    existing validation/file compatibility facade
  persistence.py               public desired/lineage store protocols + file adapter
  profile_models.py            profile result/document models
  profile_resolver.py          store-neutral inheritance and capture logic
  profile_repository.py        async repository protocol + filesystem adapter
  controller.py                stable facade + from_config construction path
  ...                          existing transport/poll/write modules remain isolated

custom_components/wolf_cwl2/
  __init__.py                  setup, typed runtime_data, unload/remove/migration
  manifest.json                local_polling, config_flow, version, pinned client
  const.py                     domain, platforms, versions, option/action names
  models.py                    immutable coordinator/runtime data types
  client.py                    config-entry -> public client construction only
  runtime.py                   sole lifecycle/operation lock and mode guards
  coordinator.py               tier deadlines, polling/reconcile, snapshot fan-out
  storage.py                   HA Store desired/lineage/profile adapters
  config_flow.py               user, reconfigure, options with reload
  entity.py                    shared CoordinatorEntity and DeviceInfo behavior
  entity_catalogue.py          load/validate HA-only declarative metadata
  entity_catalogue.json        complete entity/composite/action classification
  sensor.py                    sensor setup and value entity
  binary_sensor.py             binary sensor setup and value entity
  number.py                    safe numeric controls
  switch.py                    safe boolean controls
  select.py                    register selects and platform setup
  profile_entity.py            synthetic profile-select implementation
  date.py / time.py / text.py  only if chosen by explicit clock mapping review
  actions.py                   capture/reset registration, target resolution, guards
  diagnostics.py               redacted operational report
  repairs.py                   only actionable repair flows
  services.yaml                HA action schemas and confirmations
  strings.json
  translations/en.json

hacs.json
.github/workflows/test.yml
.github/workflows/hacs.yml
.github/workflows/hassfest.yml
```

HACS requires the runnable integration to be wholly under
`custom_components/wolf_cwl2`, a root `hacs.json`, and required manifest
metadata. Its current publication requirements and the current HA integration
layout/coordinator guidance are documented in the
[HACS integration guide](https://hacs.xyz/docs/publish/integration/),
[HA file-structure guide](https://developers.home-assistant.io/docs/creating_integration_file_structure/),
and [HA polling guide](https://developers.home-assistant.io/docs/integration_fetching_data/).

Use the Core-shaped test path now so migration later is mechanical:

```text
tests/components/wolf_cwl2/
  __init__.py
  conftest.py                  enable_custom_integrations; real app + fake gateway
  test_init.py                setup failure cleanup, reload, unload, removal
  test_config_flow.py         serial identity, duplicates, reconfigure, failures
  test_options_flow.py        modes/interval validation and exactly one reload
  test_coordinator.py         tier deadlines, single owner, recovery, cancellation
  test_multi_entry.py         isolation, one offline/one healthy, independent unload
  test_entity_catalogue.py    complete 154-key classification and dangerous exclusions
  test_sensor.py
  test_binary_sensor.py
  test_number.py
  test_switch.py
  test_select.py              unknown enums and profile lineage semantics
  test_recorder.py            units/state classes/stable IDs/no volatile attributes
  test_control_modes.py       monitor/temporary/persistent and queued desired behavior
  test_profiles.py            HA Store inheritance/apply/capture/collision/partial failure
  test_actions.py             targets, confirmation phrases, mode guards, no escape hatch
  test_storage.py             versioning, isolation, persistence, corruption/removal
  test_diagnostics.py         exhaustive sentinel redaction and error categories
  test_repairs.py             serial mismatch and corrupt storage lifecycle
  test_migration.py           current/forward schema behavior; real migrations when added
  test_package.py             manifest/HACS metadata and clean lightweight client import
  snapshots/                  reviewed registry/diagnostic snapshots only
```

Pin a `pytest-homeassistant-custom-component` release that matches the chosen
minimum HA release and Python version in a dedicated uv development group; use
`enable_custom_integrations`. Tests call HA public surfaces (`config_entries`,
state machine, services/actions, device/entity registries, Store) and replace
only `AsyncModbusTcpClient` with the existing deterministic external fake.
Do not mock coordinator/runtime/controller methods. Home Assistant's current
[testing guidance](https://developers.home-assistant.io/docs/development_testing/)
explicitly favors those public surfaces.

## Phase implications

1. **Release prerequisites and contracts:** choose license, public repository
   URL/code owner, minimum HA release, PyPI ownership, integration domain, and
   final clock/date mapping. Create the active implementation plan only under
   `.docs/plans/active/home-assistant-integration/`.
2. **Client portability (tests first):** add protocol-backed configuration and
   profile stores, direct-config construction, one-shot reconcile API if
   needed, nonblocking file adapters, log redaction, and optional Textual
   packaging. Run the existing full client/TUI suite after every split.
3. **Integration lifecycle (tests first):** create manifest/config/options flow,
   HA Store adapters, typed runtime data, one coordinator/lock, serial-based
   identity, setup cleanup, reload/unload/remove, and multi-entry isolation.
4. **Entity/Recorder surface (tests first):** approve the HA metadata catalogue,
   exhaustive classification, curated defaults, platform entities, unknown
   enum behavior, stable IDs, units/state classes, and staleness handling.
5. **Controls/profiles/actions (tests first):** mode guards, safe verified
   writes, persistent reconciliation, profile select, exact TUI-equivalent
   capture, partial failures, action target resolution, and reset confirmations.
6. **Operations and release (tests first):** diagnostics, repairs, schema gates,
   translations, README, HACS/hassfest/test workflows, client PyPI release,
   pinned manifest dependency, HACS/manual install smoke test, and GitHub
   release. Publish the client before the integration; do not push from this
   agent workflow.

Each phase should end in a working atomic commit and keep `git status` clean.
The plan cannot mark the HACS release complete until the external library
version named by the manifest is actually installable.

## System-of-record updates

Update facts where they are owned, not in a generic completion note:

- `.docs/ARCHITECTURE.md`: HA boundary, dependency direction, per-entry owner,
  and source-file split.
- `.docs/code-relationships.md`: library protocols, component platforms,
  stores, tests, HACS artifacts, and external PyPI/HA boundaries.
- `.docs/contracts/controller-api-and-json.md`: direct-config/store and
  reconciliation public contracts while preserving file users.
- `.docs/contracts/home-assistant-config-entry-and-actions.md` (new): entry and
  store versions, modes, unique IDs, action inputs/errors, profile lineage.
- `.docs/domains/home-assistant-integration.md` (new): entity catalogue,
  availability, Recorder semantics, dangerous exclusions, multi-device model.
- `.docs/decisions/002-home-assistant-package-and-poll-owner.md` (new): pinned
  lightweight library plus HA-owned scheduling/storage.
- `.docs/workflows/home-assistant-install-release.md` (new): manual/HACS install,
  client-first version order, validation, rollback, and release evidence.
- `.docs/workflows/home-assistant-physical-validation.md` (new): read-only HA
  smoke/audit and explicitly authorized write protocol; cross-link the existing
  `.docs/workflows/physical-device-validation.md`.
- `README.md`: user setup, modes, polling, entity defaults, profiles, safety,
  diagnostics, HACS/manual installation, and support boundaries.

## Risks and tradeoffs

- Publishing a library adds release ordering but avoids vendoring, Textual in
  HA, and a future Core rewrite. PyModbus compatibility with the selected HA
  version must be proven in the HA dependency environment before fixing the
  client pin.
- A coordinator tick based on the fast interval introduces at most one fast
  interval of jitter for arbitrary slow/static deadlines. If exact deadlines
  are required later, keep the same sole-owner interface and replace the
  internal scheduler; do not add parallel coordinators.
- Monitor-only state-bearing setting entities still look like native controls
  because HA has no read-only Number/Select/Switch form. Server-side rejection
  preserves stable IDs and history; changing entity domains by mode would split
  history and leave registry debris.
- Persistent mode deliberately has authority over external/local-panel drift.
  It must be explicit in setup/options and diagnostics. Temporary mode cannot
  offer meaningful TUI-equivalent capture.
- A profile select reports lineage/last application, not match. Claiming
  current match would require a separately specified comparison contract and
  fresh coherent reads after every external change.
- HA Store separates catalogues from CLI/TUI by design. Import/export and
  cross-process sharing are later features with migration/locking contracts,
  not hidden filesystem access in release one.
- All-definition exposure can create 150+ registry entries. Default-disabled
  advanced entities and a validated metadata table control UI and Recorder
  load without making capabilities unreachable.
- Repairs become noise if used for transient Modbus loss. Limit them to
  actionable identity/schema/storage faults; use availability and throttled
  logs for connectivity.

## Validation implications

Required automated gates are:

- existing `uv run pytest` client/CLI/TUI tests;
- branch coverage for the changed `wolf_325` library;
- the HA component suite against the pinned minimum HA release, including two
  simultaneous entries and cancellation/task-leak checks;
- `ruff`/type checks chosen for the repository, JSON/schema validation,
  hassfest, HACS validation, wheel build, and a clean environment installation;
- manifest/client version consistency and a clean import without Textual;
- diagnostics and log redaction using sentinel host, serial, profile text, and
  exception data;
- manual copy installation and HACS custom-repository installation in a
  disposable HA instance, followed by add/reconfigure/reload/restart/remove.

Physical validation starts from the existing verified 154-definition audit and
uses the real appliance only in monitor-only mode: add the entry, verify serial
identity locally without recording it, account for every mapped entity, confirm
153 available plus the known unsupported optional extension value, observe
fast/slow/static cadence, disconnect/reconnect the gateway, and confirm
unavailable/recovery behavior and Recorder units/state classes. A second
physical appliance is not available evidence; multiple-entry correctness is
therefore primarily deterministic simulated coverage unless the user supplies
another unit.

Any physical temporary/persistent write requires the user's explicit safe
register, original value, target value, and restore procedure. Test only one
mode at a time and verify read-back plus restoration. A multi-setting profile
apply requires separate authorization for every affected setting. Appliance
reset, filter reset, and Modbus communication writes are never part of routine
physical validation or CI. Keep endpoint credentials, serial, raw live values,
and Recorder exports out of committed evidence.
