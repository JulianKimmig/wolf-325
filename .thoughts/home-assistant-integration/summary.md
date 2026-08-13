# Home Assistant Integration

Purpose: Final synthesis across perspectives, clarifications, and four reasoning
agent results.

## Source Task

Plan a complete Home Assistant integration for the existing WOLF CWL-2
controller: time-series-ready telemetry, individual setting/control entities,
profile selection, and saving current persistent settings as a new profile.

The requested output is analysis and an implementation plan only. It does not
authorize implementation or physical writes.

## Chain-of-Thought Summary

- The existing public `wolf_325` controller, catalogue, validation, verified
  writes, desired-state reconciliation, and profile algorithms should remain
  the device/protocol system of record.
- A native HACS/manual custom integration needs a small host-neutral client
  seam first: direct runtime configuration, async desired/profile repositories,
  store-neutral profile results, controllable initial polling, and nonblocking
  file adapters.
- Each Home Assistant config entry must own one appliance runtime, one
  coordinator/scheduler, one whole-operation lock, and one versioned Store.
  Controller background polling and reconciliation remain disabled.
- Entity state must always represent confirmed appliance state. Persistent
  desired state may be queued ahead of it and requires separate summarized
  status rather than optimistic controls.
- All 154 catalogue keys need one reviewed Home Assistant disposition, but only
  a curated subset should be enabled by default. Home Assistant semantics
  cannot be inferred solely from Modbus codecs and units.
- Home Assistant-owned profile capture must preserve the TUI contract exactly:
  capture durable desired deltas relative to `last_profile`; never capture live
  telemetry or temporary writes.
- Profile lineage, last successful Home Assistant application, and live device
  match are different facts. V1 should expose the first two and avoid claiming
  automatic live profile matching.
- Release metadata, minimum Home Assistant compatibility, identity evidence,
  packed date/time UX, safe polling bounds, retry policy, and the exact default
  entity set remain explicit review items rather than facts to invent.

## Clarified Requirements

- Deliver a native custom integration for manual installation and HACS first,
  while keeping a credible route toward a future Home Assistant Core
  contribution.
- Support multiple devices/config entries from the first release.
- Configure polling intervals in seconds.
- Offer one authority mode per entry:
  - `monitor_only`: observe and record, reject all device mutations;
  - `temporary`: allow safe writes without desired-state ownership or later
    reconciliation;
  - `persistent`: persist desired ownership before I/O and reconcile after
    verified startup/reconnect and at the configured cadence.
- Give every supported datapoint an explicit entity, composite, diagnostic, or
  action-only disposition, with a curated default-enabled surface.
- Exclude dangerous Modbus communication settings and appliance reset from
  ordinary control entities. Guard dangerous actions server-side.
- Store profiles and desired lineage in Home Assistant-owned storage, not a
  filesystem directory shared live with the CLI/TUI.
- Preserve exact TUI profile-capture semantics initially.

## Synthesized Findings

### Existing reusable foundation

- `src/wolf_325/__init__.py` and
  `.docs/contracts/controller-api-and-json.md` define the stable device-library
  boundary. The integration should import only its public controller,
  catalogue, value-state, profile-result, normalization, and typed-error APIs.
- `src/wolf_325/register_catalogue.json` defines 154 values: 44 fast, 90 slow,
  18 static, and 2 never-polled. It also identifies 78 writable, 69 restorable,
  40 optional, 4 dangerous, and 2 one-shot definitions.
- `SettingsMixin.set_settings()` already performs canonical and cross-setting
  validation, persists desired ownership before I/O, orders activation-sensitive
  writes, and reports partial outcomes.
- `WriteMixin` normally verifies writes by read-back. Home Assistant should use
  those results and must not implement optimistic state assignment.
- `ProfileLoader` already owns profile names, inheritance, `replace`, `unset`,
  cycle/path safety, validation, deterministic capture deltas, collisions, and
  overwrite behavior. These algorithms should be made store-neutral rather
  than duplicated.
- Existing external-gateway fakes and tests provide a strong TDD foundation for
  lifecycle, transport, polling, write, reconciliation, profile, and safety
  behavior.

### Required client-library changes

The native integration should not create a private controller JSON file or
point `ProfileLoader` at Home Assistant's `.storage` directory. That would
create competing systems of record and retain synchronous filesystem work on
the event loop.

Add backward-compatible public seams:

- normalized direct/runtime configuration alongside `WolfCWL2(config_path=...)`;
- async desired/lineage and profile repository protocols with atomic revisioned
  mutations;
- store-neutral profile documents and save results rather than requiring a
  filesystem `Path`;
- store-independent profile resolution, whole-catalogue validation, and capture
  delta logic shared by file and Home Assistant adapters;
- lifecycle control that permits initialization without the controller's
  automatic initial poll, restoration, background loops, or state-file output;
- public one-shot reconciliation only if the current public `apply_desired`
  operation is insufficient;
- nonblocking file-backed adapters for the unchanged CLI/TUI path;
- connection/error logging that does not reveal endpoint or device identifiers;
- reusable example profiles outside CLI-only modules; and
- Textual as an optional TUI dependency, leaving the base client lightweight.

Relational setting validation needs special attention. Temporary changes must
be validated against fresh confirmed peer settings, not merely against
persistent desired state. If required peer values are unavailable or stale,
the write must fail before persistence or device I/O.

### Packaging boundary

Use a lightweight published `wolf-325` client below
`custom_components/<confirmed-domain>/`. The custom integration pins an exact,
released client version in `manifest.json`; it does not vendor a second client
copy and does not install Textual.

This sequence preserves CLI/TUI compatibility and keeps a future Core path
credible. It also creates a hard release dependency: the client wheel must be
published and qualified against the chosen Home Assistant/Python environment
before a HACS/manual integration release can reference it.

### Per-entry lifecycle and identity

One config entry represents one physical appliance/unit. Its typed runtime data
contains:

- one `WolfCWL2` instance;
- one coordinator and entry-lifetime scheduler/listener;
- one Home Assistant Store transaction owner;
- one `asyncio.Lock` covering complete high-level operations;
- immutable expected appliance identity;
- authority mode and tier/reconcile deadlines; and
- small desired/profile status records.

Setup must load/migrate storage, construct the client, initialize without a
poll or restoration, run exactly one coordinator first refresh, verify static
identity and serial, and only then restore persistent desired state. It must
never restore to an endpoint whose identity has not been verified.

The serial number is the proposed stable config-entry, device, and entity
identity. Host, port, entry ID, title, mode, and profile name must not determine
entity identity. Reconfiguration may alter endpoint fields only after proving
the same appliance serial. No host-based fallback should be invented if serial
identity proves unsuitable.

Unload marks the runtime as stopping, rejects new operations, unloads platforms,
drains a bounded active compound operation, stops the controller, and removes
listeners. Removing one entry deletes only that entry's Store. Multiple entries
have no shared mutable state.

### Polling, coordination, and availability

Home Assistant is the only scheduler. The controller runs with background poll
and reconcile loops disabled. One coordinator tick:

1. acquires the per-entry operation lock;
2. selects all due fast/slow/static/reconcile work from monotonic deadlines;
3. performs one `poll_once(tiers=due)` and any due persistent reconcile;
4. builds an immutable meaningful snapshot; and
5. releases the lock before dispatching updates.

The scheduler ticks at the minimum enabled interval, with every interval at
least Home Assistant's supported lower bound. Deadlines advance from completion
and missed cycles do not burst after an outage. An entry-lifetime listener or
equivalent single owned scheduler is required so reconciliation does not stop
when all entities are disabled.

Coordinator equality should exclude raw words, sample/generated timestamps,
and exception strings. Register entities are available only when the latest
entry refresh succeeded, the controller is connected, the value is available,
and its tier is fresh. A failed optional definition remains locally unavailable
without taking down the whole device.

Polls, individual writes, reconciliation, profile apply/capture, release, and
reset actions all take the same outer lock. The controller's internal I/O lock
is request-scoped and cannot replace this operation boundary.

### Entity and Recorder contract

Create a validated Home Assistant-only metadata overlay keyed by canonical
catalogue key. It owns platform/disposition, translation key, device/state
class, entity category, native unit, precision, default enablement, and action
policy. It must not duplicate addresses, codecs, scale, ranges, enums,
writability, or safety flags from the register catalogue.

Tests must prove every catalogue key has exactly one disposition and every
mapping references a real key. Recommended mapping principles:

- reviewed numeric telemetry becomes sensors; meaningful read booleans become
  binary sensors; read enums remain tolerant sensor states;
- safe writable numeric, enum, and boolean settings become number, select, and
  switch entities with metadata derived from `RegisterDef`;
- optional, installer, static identity, extension, and diagnostic values are
  generally disabled by default;
- the initial default surface starts from the TUI's 19 `OVERVIEW_KEYS` plus a
  reviewed small set of ordinary controls;
- dangerous communication settings are read-only diagnostic entities;
- the four packed non-restorable date/time fields require an explicit composite
  UX rather than misleading numeric controls; and
- reset registers are action-only in v1.

Stable entity unique IDs are `<serial>:<canonical-key>` plus stable semantic
suffixes for synthetic entities. Authority-mode changes must not change entity
domains or identifiers.

Recorder owns history. The integration does not write time-series data itself
and disables the controller state file. Use `MEASUREMENT` only for reviewed
instantaneous quantities. Do not assign total statistics to counters until
their monotonic/reset behavior is physically validated. Avoid `force_update`
and volatile raw/timestamp/error/desired/profile attributes.

### Authority and write semantics

| Behavior | Monitor-only | Temporary | Persistent |
|---|---:|---:|---:|
| Poll and Recorder | yes | yes | yes |
| Safe ordinary writes | reject | `persist=False` | `persist=True` when restorable |
| Non-restorable safe writes | reject | temporary | temporary |
| Profile apply | reject | settings only, no ownership mutation | atomic desired/lineage save, then sequential writes |
| Startup/reconnect/periodic reconcile | never | never | yes, after identity verification |
| Desired records | retained but inactive | retained but inactive | active |
| Profile capture save | reject | TODO; safest v1 default is reject | exact TUI capture |
| Reset actions | reject | guarded, never persistent | guarded, never persistent |

Entity state always remains the last confirmed device value. A persistent
write can fail after durable desired state has changed; the error must say the
request remains queued while the entity shows confirmed or unavailable state.
Temporary failure changes no desired ownership.

Changing away from persistent mode stops enforcement but retains dormant
desired state. Returning to persistent mode with dormant state must show the
pending keys and require explicit resume/apply or clear-ownership behavior; it
must not silently reassert old settings.

Profile and bulk writes remain sequential and may partially succeed. The outer
lock prevents local Home Assistant interleaving, not external panel/TUI/second-
instance races. There is no device transaction, rollback, or compare-and-swap.

### Profiles and actions

Use one versioned Store payload per config entry so `desired` and
`last_profile` can commit atomically. It contains at minimum a store revision,
desired mapping, lineage base, profile documents, and last successful Home
Assistant profile application. Portable profile schema versioning remains
separate from the Store version.

Persistent profile apply validates the full candidate catalogue, saves desired
plus lineage in one awaited durable mutation, and then writes sequentially.
Temporary apply writes resolved settings only; `replace` and `unset` do not
clear live device values.

Capture:

- uses only durable desired and the exact `last_profile` parent;
- excludes temporary writes and live telemetry;
- preserves inheritance, `replace`, `unset`, names, collisions, and empty-delta
  behavior;
- does no Modbus I/O;
- saves but does not apply, select, or alter lineage; and
- validates an overwrite's complete descendant graph before committing.

Preview should return a Store revision; capture may accept the expected
revision to reject a stale preview. Profile options refresh after saves without
reloading the config entry.

The profile selector is a command surface whose state is the last fully
successful Home Assistant application. `last_profile` remains capture lineage.
Neither is a claim that current live settings match a profile. A separately
named desired/profile status entity may report bounded pending/drift state only
after an explicit comparison contract is implemented.

Register actions once for the integration and require one unambiguous loaded
entry/device target. In v1:

- filter reset is action-only, control-mode gated, and requires exact
  `EXECUTE ACTION` confirmation;
- appliance reset is action-only and additionally requires a per-entry opt-in,
  exact `RESET APPLIANCE`, expected serial, live serial match, and appropriate
  Home Assistant permission;
- accepted appliance reset means command dispatched, after which the runtime
  becomes unavailable and reconnects; and
- no generic raw-register or dangerous communication-write escape hatch exists.

Confirmation strings reduce accidents but do not prove physical human presence
and remain reproducible by automations.

### Diagnostics, repair, and release operations

Diagnostics should expose versions, non-sensitive polling/mode facts, task
health, connection generation, tier success times, categorized availability
counts, and canonical unavailable keys. Redact endpoint, serial, entry IDs,
profile names/descriptions, live values, desired mappings, raw words, and
endpoint-bearing exception text. Library logs must be sanitized as well.

Use repairs only for actionable identity/schema/storage failures, not transient
Modbus disconnects. Define and test config-entry and Store versions from the
first release; add real migrations only when a schema changes.

The custom component must provide complete `translations/en.json`, manifest and
HACS metadata, action schemas, manual/HACS installation documentation, and
clean setup/reload/unload/remove behavior. Release validation includes the
client wheel, exact manifest pin, minimum Home Assistant environment,
HACS/hassfest-style checks, diagnostics redaction, and disposable manual/HACS
install smoke tests.

## Recommended Delivery Order

1. Resolve release/product TODOs and record architectural contracts.
2. Make the client host-neutral, nonblocking, safe, and lightweight while
   preserving CLI/TUI behavior.
3. Build, qualify, and publish the client artifact.
4. Implement multi-entry Home Assistant setup, storage, identity, coordinator,
   diagnostics skeleton, and read-only lifecycle.
5. Implement the complete reviewed entity/Recorder surface.
6. Add authority modes, safe confirmed controls, relational preflight,
   reconciliation, mode transitions, ownership release, and filter reset.
7. Add profile application, exact profile capture, and finally guarded
   appliance reset.
8. Finish diagnostics, repairs, translations, documentation, distribution
   checks, and read-only physical validation.

Every implementation slice follows repository TDD, updates its owning
system-of-record records, keeps Python sources below 300 lines, and ends as an
atomic commit. No physical writes or resets are part of ordinary validation.

## Risks and Tradeoffs

- Persistent mode intentionally competes with local-panel and other-controller
  changes. Dormant desired state makes re-entry into persistent mode especially
  safety-sensitive.
- A Home Assistant outer lock prevents local interleaving but cannot serialize
  an external writer or a second Home Assistant instance.
- One Store transaction owner is required for persistence-before-I/O. Delayed
  saves or separate nontransactional desired/profile stores would violate the
  existing safety invariant.
- Complete entity coverage is a long-term compatibility commitment. Platform,
  unique-ID, unit, and state-class changes can fragment history and statistics.
- Default-disabled entities still may belong to polled Modbus blocks; curation
  reduces UI/Recorder load but not necessarily device traffic.
- Publishing a separate client improves architecture but adds versioning and
  release-order discipline.
- Profile selection cannot truthfully represent live match without a more
  explicit and continuously evaluated comparison contract.
- Confirmation phrases are guardrails rather than a security boundary.

## Open Review TODOs

- **TODO: Confirm the immutable integration domain and supported model scope.**
  `wolf_cwl2` is the working recommendation.
- **TODO: Decide whether temporary mode may capture dormant historical desired
  state.** The safe v1 assumption is no.
- **TODO: Approve the composite Home Assistant UX for the four writable
  non-restorable device date/time components**, including timezone, weekday,
  ordering, and partial-failure semantics.
- **TODO: Establish a measured minimum polling interval at or above 5 seconds
  and a tier-freshness multiplier.** Existing 5/60/300-second defaults are the
  starting evidence.
- **TODO: Physically validate serial uniqueness/stability and compatible
  appliance-type values.** Do not substitute host identity if validation fails.
- **TODO: Choose bounded persistent-mismatch retry, suspension, and repair
  thresholds.** Initial implementation must at least categorize attempts and
  back off without infinite tight write churn.
- **TODO: Supply license, public repository/issue/documentation URLs, GitHub
  code owner, package publishing owner, minimum Home Assistant release, and
  supported Python versions.** These block a publishable HACS release.
- **TODO: Approve the exact default-enabled entity set and long-term-statistics
  classification of counters after metadata and physical review.**

## Explicit V1 Non-goals

- Home Assistant Core submission, discovery, TLS/authentication, an add-on,
  MQTT/API bridge, or another Modbus implementation.
- Directly shared profile files or cross-process locking with CLI/TUI.
- Automatic import/export, cross-device profile synchronization, or live-device
  profile capture.
- Writable Modbus interface/address/speed entities or a generic raw-register
  service.
- Atomic/rollback profile claims or prevention of external writers.
- Automatic live profile-match inference.
- Long-term-statistics classes for unvalidated counters.
- Routine physical profile, write, filter-reset, appliance-reset, or
  communication-setting validation.

## Validation Guidance

Automated validation must prove:

- existing CLI/TUI/controller behavior survives the library seam;
- direct config and injected repositories are store-neutral and nonblocking;
- exactly one initial poll and one periodic owner exist per entry;
- polling/reconcile stays alive with all entities disabled;
- multiple entries isolate controller, Store, locks, identities, profiles, and
  unload paths;
- availability reflects device connection, per-value result, and tier
  freshness;
- all 154 keys have one reviewed disposition and dangerous operations have no
  ordinary write escape hatch;
- entity IDs and Recorder metadata are stable and legal;
- monitor/temporary/persistent mode behavior holds across every mutation path;
- persistent failures remain queued without optimistic entity state;
- profile inheritance, application, capture, revision, collision, overwrite,
  lineage, and partial failures preserve the current contracts;
- reset gates, target resolution, permissions, invalidation, and reconnect
  behavior are enforced server-side;
- diagnostics and logs redact sentinel endpoint, identity, profile, desired,
  and exception data; and
- packaging installs the exact lightweight client in a clean supported Home
  Assistant environment.

Physical validation begins in monitor-only/read-only mode with identity,
mapping, availability, cadence/load, disconnect/reconnect, and Recorder checks.
Any write, profile, or reset validation requires separate explicit user
authorization plus original-value, restoration, and recovery evidence.

## Running Log

- Initial thought workspace created.
- One maximum-reasoning perspective agent completed general and local-resource
  passes.
- User clarified distribution, authority modes, capture semantics, storage,
  entity/dangerous-operation policy, multi-device scope, polling units, and a
  four-agent reasoning round.
- Four reasoning reports were completed with overlapping full-task analysis and
  emphases on architecture/entities, controls/profiles, delivery/testing, and
  adversarial integration review.
- Conflicts were reconciled and unresolved product/release decisions were
  retained as explicit TODOs.
