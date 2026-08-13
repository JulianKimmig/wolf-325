# Home Assistant Architecture Reasoning — Agent 1

## Source Task

Plan, but do not implement, a native Home Assistant custom integration for the
existing WOLF CWL-2-325 controller. The first distribution target is HACS and
manual `custom_components` installation, while preserving a credible path to a
future Home Assistant Core contribution. The first release must support
multiple appliances/config entries; automatically refreshed, graphable data;
individual controls and settings; profile application; and TUI-equivalent
profile capture.

The clarified product choices are binding:

- authority is selected per config entry as `monitor_only`, `temporary`, or
  `persistent`;
- profile capture uses persistent `desired` state relative to `last_profile`,
  exactly as the TUI does, rather than sampling arbitrary live registers;
- profiles are owned by Home Assistant rather than shared directly with CLI/TUI
  files;
- every supported catalogue item has an explicit Home Assistant disposition,
  but only a curated set is enabled by default;
- dangerous communication settings and appliance reset are not ordinary
  control entities; dangerous actions are guarded;
- polling intervals are configurable in seconds; and
- the work is planning/analysis only.

## Chain-of-Thought Summary

- The existing public facade is strong enough to remain the device/protocol
  boundary, but its file-backed construction and controller-owned background
  tasks do not fit Home Assistant directly.
- One Home Assistant coordinator per config entry should be the sole polling
  scheduler. It should call public `WolfCWL2.poll_once(tiers=...)`; it must not
  also enable `WolfCWL2.start(background=True)`.
- A per-entry operation lock above the controller's request lock is necessary
  to serialize whole poll cycles, individual writes, profile writes, capture,
  and reset actions. The existing `_io_lock` serializes requests, not compound
  operations.
- Stable identity should derive from the required 12-digit appliance serial,
  not host/IP. Stable entity semantics require a deliberate HA metadata layer;
  register codec/type alone is insufficient for device classes, state classes,
  categories, defaults, and long-term statistics.
- Home Assistant should own mutable desired/profile data in its storage API.
  That requires a public persistence/repository seam in `wolf_325`; creating
  private controller JSON/profile files under Home Assistant's `.storage`
  directory would retain blocking event-loop I/O and work against future Core
  compatibility.
- Profile application is sequential and may partially succeed. `last_profile`
  is capture lineage, not proof that the appliance currently matches a
  profile. The Home Assistant UX must encode that distinction.

## Findings

### Existing reusable contracts

- `WolfCWL2` in `src/wolf_325/controller.py` already provides the required
  public device operations: `start`, `stop`, `poll_once`, `refresh`,
  `snapshot`, typed setting methods, profile methods, desired reconciliation,
  and one-shot actions. `.docs/contracts/controller-api-and-json.md` declares
  this facade and `src/wolf_325/__init__.py` as the compatibility boundary.
- `RegisterDef` in `src/wolf_325/register.py` and the 154 entries in
  `src/wolf_325/register_catalogue.json` provide canonical keys, codecs, units,
  bounds, steps, enum maps, poll tiers, and the writable/restorable/dangerous/
  one-shot/optional flags. These facts must be reused, not copied into an HA
  register table.
- `PollingMixin._poll_tier()` and `WolfCWL2.poll_once()` already batch reads by
  tier. `TransportMixin._request()` serializes each Modbus request and handles
  reconnect generations/retries. Home Assistant does not need a second
  Modbus implementation.
- `SettingsMixin.set_settings()` validates the complete candidate state,
  persists desired ownership before I/O, orders activation-sensitive settings,
  and exposes partial failure through `BulkWriteError`. `WriteMixin` performs
  normal read-back verification. These are the correct write semantics for HA.
- `ProfileLoader.capture_changes()` and `save_changes()` in
  `src/wolf_325/profiles.py` implement the exact clarified capture contract.
  Tests in `tests/test_profile_capture.py` cover parent deltas, releases,
  collision guards, standalone capture, and retained lineage.
- `ValueState` has appropriate controller-level fields, but `raw`,
  `updated_at`, and `error` must not be copied onto every HA entity state as
  changing attributes. Doing so would create unnecessary Recorder churn.

### Gaps that affect the architecture

- `WolfCWL2.start(background=True)` creates three poll loops and, outside
  read-only mode, a reconcile loop. Running those together with an HA
  `DataUpdateCoordinator` would create two lifecycle owners. `start()` must be
  used with `background=False` in HA.
- The controller's `_io_lock` covers one wire request. A multi-block poll or
  multi-register `set_settings()` can otherwise interleave with another HA
  operation. The TUI avoids this with an exclusive worker group; HA needs the
  equivalent at config-entry scope.
- A transport failure can leave values in unvisited blocks with cached
  `available=True` even after the client disconnects. HA availability therefore
  cannot copy only `ValueState.available`; it must also include coordinator
  success, current connection state, and tier freshness.
- `ConfigStore` and `ProfileLoader` are path/file oriented.
  `atomic_json_write()` calls the synchronous durable writer directly,
  `read_json()` invokes its nested synchronous read directly, and profile
  discovery performs synchronous filesystem traversal. Calling this backend on
  Home Assistant's event loop is unsuitable.
- `pyproject.toml` makes Textual mandatory and does not establish that
  `wolf-325` is a published integration requirement. A custom component should
  not install Textual, and a future Core integration should consume a pinned,
  independently released client library.
- The catalogue deliberately lacks HA-specific semantics. Numeric type alone
  cannot decide whether a value is a present-time measurement, monotonic total,
  configuration number, raw diagnostic, or identifier.
- The required `serial_number` static value is the correct stable identity.
  Host/IP is explicitly unsuitable for device/entity identity because it may
  change. Config flow must not finish until serial and compatible appliance
  identity have been read.

## Proposed Architecture and Contracts

### 1. Distribution and dependency boundary

Use a custom component at `custom_components/wolf_cwl2/` with a HACS manifest
at repository root. Its `manifest.json` should declare a custom-integration
version, `config_flow: true`, `iot_class: local_polling`, the appropriate
device/hub integration type, and a pinned released `wolf-325` requirement. Do
not vendor a second copy of controller code into the component.

Make the reusable client library HA-safe first:

- keep `WolfCWL2(config_path=...)` and all existing public methods compatible;
- introduce public, typed config/desired-state and profile-repository protocols,
  plus an explicit `WolfCWL2` factory/constructor path that accepts those
  backends;
- keep `ConfigStore` and file profiles as the CLI/TUI implementations;
- let the HA component implement the protocols with Home Assistant's storage
  helper, without importing private `wolf_325` modules; and
- make Textual an optional TUI extra so the HA requirement installs only the
  controller and PyModbus dependency.

This seam must preserve the persistence-before-I/O contract of
`SettingsMixin.set_settings()`. The HA desired-state backend must durably save
before returning from `update_desired()`. The library and component must also
qualify PyModbus version compatibility with the selected Home Assistant release
before publishing the pinned requirement.

### 2. Config-entry ownership and lifecycle

One config entry represents one downstream CWL-2 appliance/Modbus unit. Do not
set `single_config_entry`; multiple entries are first-release behavior. Store a
typed runtime dataclass in `ConfigEntry.runtime_data`, containing at least:

- the `WolfCWL2` instance;
- one coordinator;
- the HA desired/profile store adapter;
- one `asyncio.Lock` for whole-operation serialization;
- immutable appliance identity/device information; and
- the selected authority mode.

Setup contract:

1. Load entry storage and create the controller using entry data/options.
2. Start it with `background=False`, `restore=False`, and `read_only=True` only
   for `monitor_only`. The controller's initial poll supplies all tiers.
3. Require a successful static identity containing the same serial as the
   config entry unique ID. Stop and raise config-entry-not-ready on transient
   communication failure; reject a different serial as a reconfiguration/
   repair error rather than silently moving the existing device.
4. In `persistent` mode only, force-apply desired state after identity is
   verified. Never restore before identity validation.
5. Publish the initial coordinator snapshot, forward entity platforms, and
   register the options-update reload listener.

Unload contract: unload all platforms, cancel coordinator scheduling/listeners,
then `await controller.stop()`. Setup failure must also stop a partially started
controller. No controller background task may remain. All domain service
actions should be registered once from integration `async_setup`, with each call
resolving and validating its targeted loaded config entry.

### 3. Configuration and options flow

The user config step collects host, port, Modbus device ID, transport
(`modbus_tcp` or `rtu_over_tcp`), and address offset. It performs a read-only
probe through the public library, reads `serial_number` plus static appliance
identity, sets the config-entry unique ID to the serial, and aborts duplicates.
The flow does not write, restore, or create persistent desired state.

Connection-defining fields belong in config-entry `data` and are changed by a
reconfigure flow. Reconfiguration must prove the new endpoint returns the same
serial. Runtime policy belongs in entry `options`:

- authority mode: `monitor_only`, `temporary`, or `persistent`;
- fast, slow, static, and persistent-reconcile intervals in seconds;
- holding-register and extension-register polling toggles; and
- advanced timeout/retry settings if exposed.

Validate positive intervals and document the 5/60/300 second controller
defaults. The implementation should set an evidence-based safe lower bound
after load testing rather than promise arbitrarily aggressive polling.
Control-enabled modes should require holding-register polling so control states
remain confirmed and graphable. Any option change reloads exactly that entry.

### 4. One coordinator and tier-aware polling

Use one `DataUpdateCoordinator` subclass per entry as the sole scheduler. Its
update interval is the shortest enabled cadence. It maintains monotonic
deadlines for `fast`, `slow`, `static`, and reconciliation work. On each tick it
collects all due poll tiers and calls `await controller.poll_once(tiers=due)`
once under the entry operation lock. After a long delay or outage, advance each
deadline from completion time; do not burst through missed intervals.

On successful completion, publish one isolated `controller.snapshot()`. Map
`CommunicationError` to `UpdateFailed`; preserve per-register optional/protocol
unavailability already represented in the snapshot. Track successful tier
times in coordinator state rather than relying only on entity timestamps.

All writes, profile applications/captures, and one-shot actions acquire the
same operation lock. They publish a new snapshot after completion or partial
failure. They must never assign optimistic entity values. Confirmed controller
read-back wins; a persistent write that fails can remain in desired state for
later reconciliation without being shown as current device state.

In `persistent` mode, coordinator reconciliation calls `apply_desired()` at the
configured cadence and force-applies after a newly observed connection
generation. `temporary` and `monitor_only` never reconcile. This reproduces the
controller's restoration behavior without enabling its reconcile loop.

### 5. Availability contract

For every normally polled register entity, `available` is true only when all
of these hold:

- the coordinator's most recent refresh succeeded;
- the controller snapshot says the client is connected;
- that value's `ValueState.available` is true; and
- its tier has completed successfully within a documented freshness window
  derived from that tier's configured interval.

This makes a transport loss immediately invalidate otherwise stale cached
values, while an unsupported optional register invalidates only itself.
Never-tier action entities use connection/authority/action-option availability,
not a cached status that normal polling never refreshes.

Authority is not device availability. To keep identifiers and Recorder history
stable across an options change, use the same entity platform in all three
modes. In `monitor_only`, readable control entities continue showing confirmed
values, but every mutation handler rejects with a localized Home Assistant
error and the controller's `read_only` guard provides defense in depth. Expose
the entry authority mode clearly in device diagnostics/documentation; do not
switch a register between `sensor` and `number` domains when the mode changes.

### 6. Device and entity identity

Create one HA device with identifier `(DOMAIN, serial_number)`, manufacturer
`WOLF`, model `CWL-2-325`, the serial, and the static software/hardware versions.
Do not use host/IP in device identifiers or entity unique IDs.

Every register-backed entity unique ID is permanently
`{serial_number}_{canonical_register_key}`. Integration-level helpers append a
stable semantic suffix, for example `{serial_number}_profile` or
`{serial_number}_desired_sync`. Entity names use translation keys and
`has_entity_name`; changing a display name must not change the unique ID.

The register-to-platform assignment is a compatibility contract. If a future
release truly needs to change it, it requires an entity-registry migration and
a Recorder/statistics continuity review.

### 7. Entity catalogue and default surface

Add a typed HA-semantic description layer keyed by every canonical catalogue
key. It may derive wire facts such as enum options, bounds, step, unit, poll
tier, and operational flags from `RegisterDef`, but it explicitly owns:

- HA platform (`sensor`, `binary_sensor`, `number`, `select`, `switch`, or
  `button`) or an explicit action-only/no-entity disposition;
- translation key;
- device class and state class;
- entity category;
- suggested display precision;
- default-enabled policy; and
- write/action policy.

An import-time validator and behavior test must prove that every one of the 154
catalogue keys has exactly one disposition and that every description refers to
a real key. Split descriptions by cohesive monitor/settings domains so source
files remain below 300 lines.

Recommended mapping rules:

- read-only live booleans become binary sensors only where boolean semantics
  are meaningful; read-only enums become textual sensors;
- restorable writable enums/bools/numerics become select/switch/number
  entities; non-restorable clock/date settings remain temporary controls even
  in persistent mode;
- high-signal operational values, based on the evidence in
  `tui_views.OVERVIEW_KEYS`, form the curated default surface;
- installer settings use `EntityCategory.CONFIG` and are mostly disabled by
  default;
- identity, firmware, raw fields, optional extension hardware, and noisy
  diagnostics are generally `DIAGNOSTIC` and/or disabled by default;
- all definitions still enter the entity registry so a user can enable the
  advanced surface intentionally;
- the three dangerous communication settings are readable diagnostic entities
  only in v1, not number/select controls; and
- filter reset may be a disabled-by-default configuration `ButtonEntity` because
  catalogue/CLI semantics classify it as non-dangerous. Appliance reset has no
  ordinary button entity.

Unknown future enum values are a contract edge: plain read-only enum sensors
preserve the library's `unknown_<raw>` state. A select must never advertise an
unknown value as writable; its current option is `None`/unknown until the device
returns a documented option, while diagnostics retain the raw controller data.

### 8. Recorder and time-series semantics

Home Assistant Recorder is the only history/time-series owner. Disable the
controller `state_file` for HA; do not duplicate snapshot history.

Entity-state contract:

- do not set `force_update`;
- expose the engineering value as entity state and stable HA metadata as
  properties;
- do not attach raw words, poll timestamps, generated timestamps, connection
  generation, or error text to every entity update;
- expose detailed raw/error/timing material through redacted diagnostics, and
  use at most a small disabled-by-default diagnostic entity for overall health;
- assign `SensorStateClass.MEASUREMENT` only to present-time numeric telemetry
  such as temperature, humidity, pressure, CO2, airflow, RPM, voltage, and
  instantaneous percentages;
- assign total semantics only where the register contract supports them. The
  operating-time and air-volume counters are candidates for
  `TOTAL_INCREASING`, including reset-cycle behavior; ambiguous numeric/raw
  fields get no state class until physically validated; and
- use HA native unit/device-class constants and validate legal combinations.
  Units and state classes are compatibility-sensitive because changing them can
  break long-term statistics continuity.

Numbers/selects/switches retain normal Recorder history when enabled, but only
sensor entities with valid state classes opt into long-term statistics. This is
enough for the requested plots without the integration writing Recorder rows
itself.

### 9. Authority modes and write behavior

Define mode semantics as a contract, not a UI hint:

| Mode | Controller guard | Ordinary write/profile apply | Restore/reconcile | Capture |
|---|---|---|---|---|
| `monitor_only` | `read_only=True` | rejected | never | rejected, matching TUI read-only behavior |
| `temporary` | writable | always `persist=False` | never | allowed, but captures previously persistent desired ownership; temporary writes are excluded |
| `persistent` | writable | `persist=True` for restorable values; non-restorable values remain temporary | startup/reconnect/periodic | allowed |

All entity handlers validate through `RegisterDef` and call public controller
methods. No entity assigns an optimistic value. Translate typed domain errors
to localized HA exceptions. A partial bulk write must surface an error while
publishing whatever confirmed results are available. Persistent desired state
may be ahead of confirmed device state by design; an overall desired-sync
diagnostic can show synchronized/pending/error without adding volatile desired
attributes to every control entity.

### 10. Profiles and Home Assistant storage

Use a versioned HA Store record per config entry containing at least `desired`,
`last_profile`, profile documents, and separate HA UI metadata such as
`last_applied_profile`. The first initialization may copy the five canonical
examples currently owned by `cli_init.EXAMPLE_PROFILES`; it must never overwrite
user records on later loads. Move that default mapping to a reusable public
library location rather than importing `cli_init` from HA.

The repository-backed profile service must retain existing validation,
inheritance, merge/replace/unset, deterministic ordering, and atomic/collision
semantics. Store updates and controller operations share the entry operation
lock. Add storage schema migrations before changing profile documents or
desired lineage.

Provide a profile `SelectEntity` whose options refresh immediately after a
successful save. Its state is explicitly **last successfully applied through
Home Assistant**, not “device currently matches profile.” Keep that UI field
separate from core `last_profile`: the latter remains persistent capture
lineage, and temporary applications must not alter it. A partial profile apply
does not advance the UI's last-successful value.

Register translated domain actions once at integration setup:

- preview profile/capture delta with a response;
- apply a named profile using the entry's authority mode;
- save/capture a profile with required name, optional description, and
  overwrite defaulting false; and
- optionally release selected desired keys without writing replacement values.

Capture must call the same core delta logic as the TUI. It performs no live
poll or device write, excludes temporary changes, saves without applying, and
refreshes profile-select options after success. Direct cross-process sharing
or locking with the CLI/TUI profile directory is outside v1; import/export can
be a later explicit migration feature.

### 11. Dangerous operations

Do not create ordinary writable entities for Modbus interface type, slave
address, speed, or appliance reset. In v1, communication settings remain
readable diagnostics only because a successful write can invalidate both the
connection and config-entry endpoint; adding them later requires a transactional
reconfigure/recovery design.

Expose appliance reset, if included in v1, only as a domain action with two
gates: a per-entry `allow_dangerous_actions` option defaulting false and the
exact `RESET APPLIANCE` confirmation value on every call. It must also reject
`monitor_only`, run under the operation lock, call
`reset_appliance(confirm=True)`, mark device entities unavailable, and let the
normal coordinator reconnect. Document that an action confirmation string also
works from automations and is not a human-presence guarantee.

The filter-reset button remains non-dangerous by catalogue contract but should
be disabled by default and categorized as configuration/maintenance.

## Phased Work Implications

1. **Contracts and library seam.** Update `.docs/ARCHITECTURE.md`,
   `.docs/code-relationships.md`, the controller API contract, controller
   domain, profile workflow, and a new HA workflow/contract. Write backend
   contract tests first, then add the injectable persistence/profile boundary,
   reusable example profiles, and optional Textual packaging without changing
   existing file/CLI/TUI behavior.
2. **HA package and config lifecycle.** Add HACS/custom-component metadata,
   translations, config/reconfigure/options flows, typed runtime data, the
   per-entry Store adapter, identity probe, setup/unload/reload, and diagnostics
   skeleton. Prove two simultaneous config entries and serial-based duplicate
   prevention before entity work.
3. **Coordinator and availability.** Test tier deadlines, initial refresh,
   outage/backoff, reconnect generation, staleness, optional-register isolation,
   no background controller tasks, and operation-lock exclusion; then implement
   the sole coordinator and base entity.
4. **Entity semantic catalogue.** Write coverage and metadata tests for all 154
   keys, Recorder/state-class constraints, stable unique IDs, curated defaults,
   and dangerous exclusions; then implement sensor/binary sensor/number/select/
   switch/button platforms in cohesive modules.
5. **Controls, modes, profiles, and guarded actions.** Test the three authority
   modes, confirmed writes, partial failures, persistence-before-I/O, reconnect
   reconcile, HA Store lineage/migrations, TUI-equivalent capture, dynamic
   profile options, and dangerous gates before implementation.
6. **Distribution validation.** Add user documentation for HACS/manual setup,
   network and mode safety, entity enablement, Recorder behavior, profile
   semantics, and recovery. Validate the manifest/HACS structure, a clean HA
   install of the pinned library, unload/reload cycles, and read-only physical
   polling before release. Never run physical write/reset tests without a
   separately authorized target and restore procedure.

## Risks and Tradeoffs

- **Storage refactor scope:** an injectable backend is more work than generating
  private files, but it avoids blocking Home Assistant's event loop, duplicate
  config state, and a dead-end for Core.
- **Monitor-only UX:** HA has no generic read-only number/select/switch state.
  Keeping the platform stable preserves visibility/history but controls still
  look actionable; localized rejection plus obvious mode diagnostics and the
  controller read-only guard are required.
- **Profile state ambiguity:** no select can prove ongoing device/profile match
  in the face of local-panel writes, normalization, partial profiles, or manual
  edits. “Last successfully applied” and persistent `last_profile` lineage must
  remain distinct and documented.
- **No appliance transaction:** profile and bulk writes are sequential.
  Operation locking prevents HA interleaving but cannot make device writes
  atomic or roll back a partial application.
- **External writers:** HA cannot prevent the TUI, local panel, or another
  controller from changing the appliance. Persistent mode intentionally
  reasserts ownership; temporary/monitor modes do not.
- **Polling load:** a configurable one-second interval could overload the
  gateway and Recorder-facing state machine. Lower bounds need measured
  evidence, and disabled entities do not eliminate block reads.
- **Dependency conflicts:** the pinned PyModbus release and Home Assistant's
  environment must be qualified. Mandatory Textual is unacceptable for the HA
  requirement.
- **Entity contract breadth:** 154 dispositions are a maintenance commitment.
  Coverage tests and a curated enabled subset limit drift and UI noise.
- **Enum evolution:** `unknown_<raw>` is observable in sensor states but cannot
  become an automatically writable select option.
- **Serial assumptions:** setup depends on serial being readable and unique.
  If physical validation disproves that assumption, a migration-safe hardware
  identifier strategy is required before release; host is not an acceptable
  fallback.
- **Danger confirmations:** a string in a service call guards accidents, not
  malicious or unattended automation. Dangerous actions must be opt-in and
  narrowly scoped.

## Validation Implications

Repository TDD rules require behavior tests before each code change. Use the
real catalogue, codecs, validation, profile resolution, controller ordering,
and persistence semantics; replace only the external gateway and HA runtime
boundaries.

Minimum automated evidence:

- existing controller/CLI/TUI tests remain green with both file and injected
  backends;
- config flow rejects unreachable/incompatible endpoints, aborts duplicate
  serials, accepts two distinct devices, and reconfigure refuses a changed
  serial;
- setup failure cleans up, unload closes transport, reload replaces exactly one
  runtime, and no controller polling/reconcile task runs behind the coordinator;
- fake time proves fast/slow/static cadence, no missed-interval burst, tier
  freshness, reconnect force-restore only in persistent mode, and no overlap
  between poll, setting, profile, capture, and reset operations;
- transport loss makes all entities unavailable, while optional register or
  decode failure affects only its entities and recovery restores availability;
- every catalogue key has exactly one HA disposition; dangerous communication
  registers and appliance reset have no ordinary writable entity; default
  enablement remains curated;
- unique IDs survive host/reconfigure/options changes and two appliances do not
  collide;
- entity properties assert legal native-unit/device-class/state-class
  combinations, no forced updates, and absence of volatile raw/timestamp/error
  attributes; counter reset sequences test chosen long-term-statistics
  semantics;
- monitor mode produces zero writes through every entry point; temporary mode
  never changes desired/lineage; persistent mode saves before I/O and retries
  queued desired state after reconnect; non-restorable controls never persist;
- profile Store migration, inheritance, replace/unset, collision, empty delta,
  parent retention, temporary exclusion, partial apply, last-successful UI
  state, and option-list refresh all behave as contracted; and
- diagnostics redact host, serial, desired values/profile content as selected by
  the privacy contract while retaining useful availability/error/tier evidence.

Physical validation remains additive and read-only initially: confirm identity,
units, optional modules, poll cost at candidate cadences, counter monotonic/reset
behavior, and Recorder graphs. Live write, profile, filter reset, communication
setting, and appliance reset tests require explicit separate authorization and
a recovery/restore plan under `.docs/workflows/physical-device-validation.md`.
