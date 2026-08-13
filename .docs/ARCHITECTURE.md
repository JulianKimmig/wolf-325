# WOLF 325 architecture

## Purpose and authority

This repository packages an asynchronous Python 3.11+ controller for a WOLF
CWL-2-325 reached through a Modbus TCP-to-RTU gateway. The port must preserve
the behavior of the external reference implementation in
[`wolf_cwl2.py`](../.guides/wolf_cwl2_async/wolf_cwl2.py) while replacing its
single-file structure with the modular `wolf_325` package described here.

The installed package under [`src/wolf_325`](../src/wolf_325) is the runtime
system of record. The reference guide remains the behavioral migration baseline
until its catalogue, API, persistence, polling, profile, CLI, and error behavior
are covered by package tests. The guide is not imported by production or test
code.

See the [controller domain](domains/cwl2-controller.md), [public, JSON, and
operator-interface contracts](contracts/controller-api-and-json.md), [code
relationships](code-relationships.md), [physical-device validation
workflow](workflows/physical-device-validation.md), and [TUI operation
workflow](workflows/tui-operation.md). Saving current desired-state deltas is
defined by the [profile capture workflow](workflows/profile-capture.md). The
planned native host adapter is governed by the [Home Assistant domain](domains/home-assistant-integration.md)
and [config-entry/Store contract](contracts/home-assistant-config-entry-and-store.md).
Its local packaging and externally blocked publication gates are owned by the
[Home Assistant release workflow](workflows/home-assistant-release-validation.md).

## Package boundaries

The port uses the following ownership boundaries. A path listed here is a
required package boundary; its presence by itself does not prove the port is
complete.

| Path | Owned responsibility |
|---|---|
| [`types.py`](../src/wolf_325/types.py) | Shared JSON, table, polling-tier, callback, and result types. |
| [`errors.py`](../src/wolf_325/errors.py) | Public exception hierarchy and partial bulk-write error data. |
| [`register.py`](../src/wolf_325/register.py) | Register metadata plus normalization, encode, decode, and comparison behavior. |
| [`catalogue.py`](../src/wolf_325/catalogue.py) | Catalogue loading, name aliases, lookup, read blocks, and catalogue integrity checks. |
| [`register_catalogue.json`](../src/wolf_325/register_catalogue.json) | Declarative metadata for all 154 reference logical values. |
| [`config.py`](../src/wolf_325/config.py) | Schema-version-1 configuration validation, deep merge, path resolution, and atomic JSON persistence. |
| [`runtime_config.py`](../src/wolf_325/runtime_config.py) | Host-neutral configuration repository protocol and awaited in-memory persistence adapter. |
| [`async_utils.py`](../src/wolf_325/async_utils.py) | Explicit worker ownership for blocking external filesystem calls. |
| [`profile_models.py`](../src/wolf_325/profile_models.py) | Store-neutral public resolved, delta, and saved profile result models. |
| [`profile_engine.py`](../src/wolf_325/profile_engine.py) | Store-neutral inheritance, merge/replace/unset, graph validation, and capture behavior. |
| [`profiles.py`](../src/wolf_325/profiles.py) | Filesystem and host-owned in-memory profile repository adapters. |
| [`example_profiles.py`](../src/wolf_325/example_profiles.py) | Isolated portable example profile documents shared by CLI and embedded hosts. |
| [`state.py`](../src/wolf_325/state.py) | Cached value-state and serialized snapshot/update shapes. |
| [`transport.py`](../src/wolf_325/transport.py) | PyModbus client construction, connection generations, retries, protocol error classification, and serialized I/O. |
| [`polling.py`](../src/wolf_325/polling.py) | Tier/block polling and unavailable-state handling. |
| [`writes.py`](../src/wolf_325/writes.py) | Low-level validated writes and read-back verification. |
| [`settings.py`](../src/wolf_325/settings.py) | Public setters, desired-state ordering/reconciliation, active-profile lineage, profile application, and one-shot commands. |
| [`setting_relations.py`](../src/wolf_325/setting_relations.py) | Fresh confirmed-peer preflight for relational setting groups. |
| [`controller.py`](../src/wolf_325/controller.py) | Stable `WolfCWL2` facade, lifecycle, state subscriptions, profile apply/capture, and reconciliation orchestration. |
| [`cli.py`](../src/wolf_325/cli.py) | Argument parsing and async command dispatch, including local profile capture without device startup. |
| [`__main__.py`](../src/wolf_325/__main__.py) | `python -m wolf_325` entry point only. |
| [`tui.py`](../src/wolf_325/tui.py) | Standalone `wolf-cwl2-tui` argument parsing and Textual application launch. |
| [`tui_app.py`](../src/wolf_325/tui_app.py) | Textual layout, controller lifecycle, snapshot redraw, selection, and event dispatch. |
| [`tui_service.py`](../src/wolf_325/tui_service.py) | Safety-aware adapter from TUI operations and derived-profile capture to the public `WolfCWL2` API. |
| [`tui_operations.py`](../src/wolf_325/tui_operations.py) | Interactive actions, exclusive operation workers, profile-save dispatch, activity logging, and notifications. |
| [`tui_dialogs.py`](../src/wolf_325/tui_dialogs.py) | Register-write, profile-review/apply, and derived-profile capture modal screens. |
| [`tui_models.py`](../src/wolf_325/tui_models.py) | Pure table/detail/search/editor presentation models derived from catalogue and snapshots. |
| [`tui_navigation.py`](../src/wolf_325/tui_navigation.py) | Complete monitor/settings taxonomy that partitions the catalogue. |
| [`tui_views.py`](../src/wolf_325/tui_views.py) | Quick/domain view resolution and navigation-tree construction. |
| [`tui.tcss`](../src/wolf_325/tui.tcss) | Textual layout, colors, sizing, and modal presentation. |
| [`__init__.py`](../src/wolf_325/__init__.py) | Deliberate public re-exports only. |

The Home Assistant host adapter currently has these package boundaries:

| Path | Owned responsibility |
|---|---|
| [`custom_components/wolf_cwl2/__init__.py`](../custom_components/wolf_cwl2/__init__.py) | Home Assistant package and config-entry lifecycle. |
| [`custom_components/wolf_cwl2/const.py`](../custom_components/wolf_cwl2/const.py) | Immutable integration identity and shared host constants. |
| [`custom_components/wolf_cwl2/config_flow.py`](../custom_components/wolf_cwl2/config_flow.py) | Serial-backed user/reconfigure flow and automatic-reload runtime options. |
| [`custom_components/wolf_cwl2/config_schema.py`](../custom_components/wolf_cwl2/config_schema.py) | End-user connection/policy forms and hard polling-floor validation. |
| [`custom_components/wolf_cwl2/probe.py`](../custom_components/wolf_cwl2/probe.py) | Read-only public-client identity probe with deterministic cleanup and flow-safe errors. |
| [`custom_components/wolf_cwl2/entry_config.py`](../custom_components/wolf_cwl2/entry_config.py) | Translation from config-entry data/options and Store state to complete public-client configuration. |
| [`custom_components/wolf_cwl2/coordinator.py`](../custom_components/wolf_cwl2/coordinator.py) | Sole tier/reconciliation deadline scheduler, whole-operation poll owner, reconnect identity gate, and freshness/publication owner. |
| [`custom_components/wolf_cwl2/entity_catalogue.py`](../custom_components/wolf_cwl2/entity_catalogue.py) | Exhaustive HA-only semantic overlay and curated entity defaults; imports but never duplicates the client catalogue. |
| [`custom_components/wolf_cwl2/entity.py`](../custom_components/wolf_cwl2/entity.py) | Common serial identity, device grouping, translated naming, registry defaults, and cache/tier availability behavior. |
| [`custom_components/wolf_cwl2/mutations.py`](../custom_components/wolf_cwl2/mutations.py) | Authority-gated, whole-operation serialized, translated mutation and confirmed-cache publication boundary. |
| [`custom_components/wolf_cwl2/profile_operations.py`](../custom_components/wolf_cwl2/profile_operations.py) | Mode-aware, serialized profile application and truthful success-marker publication through the public profile engine. |
| [`custom_components/wolf_cwl2/services.py`](../custom_components/wolf_cwl2/services.py), [`services.yaml`](../custom_components/wolf_cwl2/services.yaml) | Integration-level response-capable service registration and operator-facing action schemas. |
| [`custom_components/wolf_cwl2/service_helpers.py`](../custom_components/wolf_cwl2/service_helpers.py) | Shared exact-one-loaded-entry resolution for integration-level actions. |
| [`custom_components/wolf_cwl2/reset_services.py`](../custom_components/wolf_cwl2/reset_services.py) | Action-only filter/appliance reset gates, live identity verification, dispatch, and reconnect invalidation. |
| [`custom_components/wolf_cwl2/diagnostics.py`](../custom_components/wolf_cwl2/diagnostics.py) | Privacy-by-construction config-entry/device operational summaries with second-layer key redaction. |
| [`custom_components/wolf_cwl2/repairs.py`](../custom_components/wolf_cwl2/repairs.py) | Opaque per-entry actionable issue identifiers and persistent issue lifecycle. |
| [`custom_components/wolf_cwl2/button.py`](../custom_components/wolf_cwl2/button.py) | Explicit resume and clear transitions for persistent desired ownership. |
| [`custom_components/wolf_cwl2/number.py`](../custom_components/wolf_cwl2/number.py), [`select.py`](../custom_components/wolf_cwl2/select.py), [`switch.py`](../custom_components/wolf_cwl2/switch.py) | Native safe control factories plus the synthetic HA-owned profile selector. |
| [`custom_components/wolf_cwl2/runtime.py`](../custom_components/wolf_cwl2/runtime.py) | Typed per-entry resource bundle and `ConfigEntry` alias. |
| [`custom_components/wolf_cwl2/sensor.py`](../custom_components/wolf_cwl2/sensor.py) | Factory and generic sensor implementation for all reviewed read dispositions. |
| [`custom_components/wolf_cwl2/manifest.json`](../custom_components/wolf_cwl2/manifest.json) | Custom-component metadata, public documentation/issues, and approved code owner; only the exact unpublished client requirement remains blocked. |
| [`custom_components/wolf_cwl2/brand`](../custom_components/wolf_cwl2/brand) | Local custom-integration imagery for Home Assistant 2026.3 and newer; it carries no runtime behavior. |
| [`custom_components/wolf_cwl2/storage_models.py`](../custom_components/wolf_cwl2/storage_models.py) | Versioned JSON-safe per-entry payload construction and fail-closed validation. |
| [`custom_components/wolf_cwl2/storage_backend.py`](../custom_components/wolf_cwl2/storage_backend.py) | Private atomic Home Assistant Store wrapper and explicit supported wrapper/payload migrations. |
| [`custom_components/wolf_cwl2/storage_errors.py`](../custom_components/wolf_cwl2/storage_errors.py) | Sanitized persistence failures and stable actionable fault categories. |
| [`custom_components/wolf_cwl2/storage.py`](../custom_components/wolf_cwl2/storage.py) | Single per-entry HA Store transaction owner, verified desired/lineage commits, profile adapter, and scoped removal. |
| [`custom_components/wolf_cwl2/storage_profiles.py`](../custom_components/wolf_cwl2/storage_profiles.py) | Profile repository construction and complete inheritance-graph validation extracted from Store transaction code. |
| [`custom_components/wolf_cwl2/translations/en.json`](../custom_components/wolf_cwl2/translations/en.json) | Complete custom-integration English strings without Core-only placeholders. |
| [`hacs.json`](../hacs.json) | Root HACS repository display metadata for the public integration repository. |

If controller lifecycle code needs mixins or additional cohesive modules, they
remain behind `WolfCWL2`; callers must not depend on the internal split.

## Dependency direction

Dependencies flow inward from entry points to domain and infrastructure:

```text
__main__ -> cli -> controller
                    |-> polling -> transport
                    |-> settings -> writes -> transport
                    |-> config/runtime_config
                    |-> profiles -> profile_engine/profile_models
                    |-> state
register_catalogue.json -> catalogue -> register
tui console -> tui -> tui_app
                     |-> tui_views -> tui_navigation -> catalogue
                     |-> tui_models -> register/catalogue
                     |-> tui_operations -> tui_dialogs/tui_service
                     |-> tui_service -> controller/catalogue
all package modules -> types/errors as needed
```

`register.py`, catalogue metadata, configuration normalization, and profile
resolution must not depend on the live transport. This keeps codec and
persistence behavior testable without a device. `transport.py` owns PyModbus;
no other module talks directly to a PyModbus client. The TUI reaches config,
profiles, state, and the device only through `WolfCWL2` and
`ControllerTuiService`; presentation modules do not implement control logic.

## Runtime invariants

- All public device operations are asynchronous. Blocking filesystem reads,
  writes, discovery, and durable replacement run through an explicitly owned
  worker; Modbus I/O never blocks through synchronous sockets.
- All Modbus requests made through one client are serialized. Polling,
  reconciliation, and explicit writes must not use the client concurrently.
- Optional-register protocol exceptions mark only the affected values
  unavailable. Transport/no-response errors close the client and initiate the
  retry/reconnect path.
- A connected short response for an optional block falls back to individual
  definition reads. A repeatable zero-word optional definition is marked
  unavailable without invalidating the connection; see
  [decision 001](decisions/001-optional-zero-word-responses.md).
- Desired settings are validated and atomically persisted before their Modbus
  writes. A failed device write leaves the desired value queued for later
  restoration.
- File-backed CLI/TUI callers use `WolfCWL2(config_path=...)`. Embedded hosts
  use `WolfCWL2.from_config(...)` with awaited configuration/profile
  repositories, disabled client-owned state paths, and explicit initial-poll,
  restore, and background-task ownership.
- Relational changes refresh every omitted peer in the affected constraint
  group and fail before persistence or writes when the resulting live candidate
  is invalid or unavailable.
- Restorable settings may be force-written at startup and after a new
  connection generation. Dangerous communication settings, clock/date values,
  and one-shot commands are never restored automatically.
- Source modules stay below the repository's 300-line limit; the stable facade
  delegates rather than accumulating implementation detail.
- TUI controls and service guards both enforce read-only mode. Editor types,
  persistence eligibility, and validation constraints derive from canonical
  register metadata; TUI policy maps dangerous/one-shot metadata to its exact
  confirmation phrases without creating a second setting schema.
- TUI device operations use one exclusive worker group, while periodic redraws
  copy public snapshots and never issue Modbus reads by themselves.
- Profile capture is a local transformation of canonical persistent desired
  state. It may read a parent profile and atomically write one profile document,
  but it does not read/write the device, activate the saved profile, or mutate
  desired state and `last_profile`.
- Persistently applying a profile sets `last_profile`; later persistent setting
  changes and desired-key releases retain that marker so capture can derive a
  child from the active base.

## External boundaries

The required runtime library boundaries are PyModbus's async TCP client and
Textual 8.x for the terminal application. The device boundary is the Waveshare
gateway and the downstream WOLF/UWA2 Modbus unit. JSON configuration, profile,
and state files are local persistence interfaces and are defined in the
[contract record](contracts/controller-api-and-json.md).

The [`custom_components/wolf_cwl2`](../custom_components/wolf_cwl2) boundary is
a host adapter: it may depend on
the public `wolf_325` facade and Home Assistant APIs, while `src/wolf_325` must
never import Home Assistant. Home Assistant owns config-entry lifecycle,
scheduling, entity semantics, and Store persistence. This one-way dependency is
recorded before component behavior is added so the host cannot become a second
Modbus implementation.

At runtime, `__init__.py` is the only config-entry lifecycle owner. It loads the
Store, builds one client, starts it without implicit reads/restoration/tasks,
performs one coordinator-owned all-tier refresh, verifies the expected serial,
retains one scheduler listener independent of entities, and only then forwards
platforms. Unload removes platforms and cadence before stopping transport under
the entry operation lock.
