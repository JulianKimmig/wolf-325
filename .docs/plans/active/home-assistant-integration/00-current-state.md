# Current State And Preserved Requirements

## Product Interpretation

This project already controls a WOLF CWL-2-325 through a Waveshare
TCP-to-Modbus gateway. The requested work adds a native Home Assistant host
adapter; it does not replace the controller, introduce another Modbus stack, or
turn Home Assistant into a shell-command wrapper.

The user journey is:

1. Add one or more appliances through Home Assistant's UI.
2. Observe stable, automatically refreshed entities and plot appropriate
   numeric telemetry through Recorder and long-term statistics.
3. Enable advanced or diagnostic entities when needed without cluttering a
   default installation.
4. Choose the authority level for each appliance.
5. Change safe settings through native entities and receive truthful failures.
6. Apply a named profile as one serialized multi-setting operation.
7. In persistent mode, preview and save current persistent desired ownership as
   a new profile without reading arbitrary live telemetry.

## Existing Repository State

- Python 3.11+ project managed by `uv` with `pyproject.toml` and `uv.lock`.
- Public async controller facade in `src/wolf_325/__init__.py` and
  `src/wolf_325/controller.py`.
- Canonical 154-definition schema in
  `src/wolf_325/register_catalogue.json`, exposed through `RegisterDef` and
  `REGISTERS`.
- Tiered fast/slow/static polling, cached snapshots, subscriptions, verified
  writes, persistent desired state, reconnect restoration, profiles, CLI, and
  Textual TUI.
- Current defaults are approximately 5 seconds fast, 60 seconds slow, 300
  seconds static, and 30 seconds reconciliation.
- `SettingsMixin.set_settings()` validates, persists desired state before I/O,
  orders activation-sensitive values, and reports partial failure.
- `WriteMixin` normally confirms writes by read-back.
- `ProfileLoader` provides names, inheritance, `replace`, `unset`, graph/path
  safety, validation, deterministic capture deltas, collision guards, and
  atomic file replacement.
- TUI capture saves persistent `desired` deltas relative to `last_profile`; it
  does not capture live register state and does not apply/select a saved
  profile.
- `ConfigStore` and `ProfileLoader` are filesystem-oriented, and some nominally
  async JSON/profile operations perform blocking filesystem work.
- `WolfCWL2.start()` performs an initial poll and can own three background poll
  tasks plus reconciliation. Its internal I/O lock serializes requests, not a
  whole poll/profile/bulk operation.
- Textual is currently a mandatory project dependency.
- No custom component, config flow, HA Store adapter, HA entity metadata,
  translations, HACS metadata, diagnostics, repairs, HA test harness, or
  published-client release contract exists.
- Existing physical tests are opt-in and read-only.

## Source-Derived Requirements

- HACS/manual native custom integration first; retain a credible Core path.
- Multiple appliances/config entries from the first release.
- Configurable fast, slow, static, and reconciliation polling in seconds.
- Complete explicit disposition of supported datapoints with curated defaults.
- Recorder-compatible stable identities, units, state classes, and history.
- Per-entry monitor-only, temporary, and persistent authority.
- Confirmed device state in entities; never optimistic requested state.
- Home Assistant-owned versioned desired/profile storage.
- Profile selection/application and exact TUI-equivalent capture.
- Guarded reset actions; no normal control entities for dangerous Modbus
  communication settings or appliance reset.
- Test-first implementation, modular source below 300 lines, accurate durable
  documentation, atomic commits, a clean worktree, and no unauthorized pushes.

## Source-Derived Constraints

- Use only the public `wolf_325` facade from the Home Assistant layer.
- Preserve `WolfCWL2(config_path=...)`, CLI, TUI, and file-backed profiles.
- Keep the register catalogue as the wire/device schema system of record.
- Give Home Assistant one polling/reconciliation owner and one whole-operation
  lock per entry.
- Verify appliance identity before persistent restore or endpoint reconfigure.
- Persist desired state and lineage durably before the first persistent write.
- Treat a bulk/profile apply as sequential and partially fallible; do not claim
  transactions or rollback.
- Keep profile lineage, last successful HA apply, and live match distinct.
- Keep raw words, volatile timestamps, exception strings, desired maps, and
  profile documents out of ordinary Recorder attributes.
- Start physical validation in monitor-only/read-only mode.

## Forbidden Or Rejected Approaches

- A command-line/shell entity adapter, MQTT bridge, external daemon, add-on, or
  second Modbus implementation for v1.
- Vendoring a duplicate controller into `custom_components`.
- Generating a hidden controller JSON/profile directory in Home Assistant's
  `.storage` area.
- Running controller background loops and a Home Assistant coordinator
  simultaneously.
- Per-entity network polling or I/O from entity properties.
- Host/IP-based unique IDs or silent fallback identity.
- Optimistic entity state after writes.
- Generic raw-register write actions.
- Ordinary writable entities for Modbus interface/address/speed or appliance
  reset.
- Shared live profile files with CLI/TUI, implicit cross-device sync, or live
  register capture.
- `strings.json` as the custom integration localization source.
- Long-term-statistics classes inferred from numeric codecs without evidence.
- Physical writes/resets without separate authorization and recovery evidence.

## Design Rationale To Preserve

- A host-neutral client seam costs more than private HA files but avoids two
  systems of record, blocking event-loop I/O, and a future Core rewrite.
- Coordinator ownership aligns availability, setup retry, unload, and entity
  publication while the outer lock closes the compound-operation race left by
  the request-level transport lock.
- Confirmed writes are slower than optimistic UI updates but remain truthful
  under device normalization, verification mismatch, and offline queued
  persistent ownership.
- Complete metadata coverage prevents silently lost capabilities; curated
  defaults limit UI and Recorder noise.
- HA Store separation avoids cross-process profile races. A portable profile
  schema preserves a later import/export path without adding live file sharing.
- A profile select cannot prove ongoing match after external writes or partial
  application, so v1 must not present it as live truth.

## User Goals And Success Criteria

- Home Assistant discovers all deliberately supported capabilities through
  stable entities/actions.
- Relevant telemetry can be graphed without custom Recorder writes.
- Unavailable or stale device data is not presented as current.
- Safe controls work under the configured authority and surface validation,
  communication, verification, persistence, and partial failures accurately.
- Profiles apply deterministically and capture exactly the persistent TUI
  source semantics.
- Multiple entries remain isolated through setup, polling, writes, profiles,
  reload, unload, and removal.
- A clean supported Home Assistant installation can install the exact pinned
  lightweight client and load the custom integration without Textual.

## Scope

Included: client portability, published dependency, native component lifecycle,
multi-device config/reconfigure/options, HA Store, polling, complete entity
metadata, read entities, safe controls, authority modes, reconciliation,
profiles, capture, guarded reset actions, diagnostics, repairs, migrations,
translations, tests, docs, HACS/manual validation, and read-only physical
validation.

## Non-Scope

Core submission itself, discovery, TLS/authentication, broker/API bridges,
automatic profile import/export, shared profile directories, communication
setting writes, generic register access, automatic live profile matching,
unvalidated counter statistics, and routine physical writes/resets.

## Constraints And Instructions

- Follow repository TDD: tests precede every implementation behavior change.
- Mock only external resources such as the gateway and Home Assistant host
  boundary; do not replace source logic under test.
- Use `uv` for Python commands and discover exact new commands before recording
  them as durable workflow facts.
- Every source file begins with the required detailed docstrings and stays below
  300 lines.
- Update the owning system-of-record document with each behavior change.
- Do not delete unrelated files and never push.

## Assumptions

- The confirmed domain is `wolf_cwl2` for the generation-1 CWL-2-325 scope.
- Temporary-mode capture is rejected in v1.
- Poll intervals have a five-second floor and values become stale after two
  missed configured intervals.
- The verified 12-digit serial is the stable identity; one-device physical
  evidence does not prove fleet-wide uniqueness.
- Home Assistant owns one versioned Store payload per config entry.
- Custom integration and client remain separately versioned release artifacts.

## Unknowns

Blocking before publishable implementation:

- exact trusted-publisher/release authorization. The sanitized initial source
  push is complete; archival development history remains local.

No local behavior decision remains unresolved. The accepted first-release
choices are:

- read-only date/time exposure without a composite write action;
- categorized reconciliation without an invented suspension threshold;
- the reviewed default-enabled entity overlay; and
- no total statistic classes for counters lacking semantic evidence.

Broader fleet identity and counter semantics remain explicitly bounded evidence
limits rather than silently generalized claims.
