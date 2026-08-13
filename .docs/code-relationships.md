# Code relationships

This map links the reference behavior, package ownership, tests, persisted
formats, and physical device. Architecture rules live in
[`ARCHITECTURE.md`](ARCHITECTURE.md); value and lifecycle semantics live in the
[`cwl2-controller` domain record](domains/cwl2-controller.md).

## Reference-to-package map

| Reference area | Package owner | Primary behavioral tests |
|---|---|---|
| Exceptions and shared aliases in [`wolf_cwl2.py`](../.guides/wolf_cwl2_async/wolf_cwl2.py) | [`errors.py`](../src/wolf_325/errors.py), [`types.py`](../src/wolf_325/types.py), public exports in [`__init__.py`](../src/wolf_325/__init__.py) | [`test_controller.py`](../tests/test_controller.py) and importing tests |
| `RegisterDef`, codecs, aliases, register definitions, and `READ_BLOCKS` | [`register.py`](../src/wolf_325/register.py), [`catalogue.py`](../src/wolf_325/catalogue.py), [`register_catalogue.json`](../src/wolf_325/register_catalogue.json) | [`test_catalogue_codecs.py`](../tests/test_catalogue_codecs.py) |
| File and host-neutral configuration, desired persistence, and off-loop atomic JSON | [`config.py`](../src/wolf_325/config.py), [`runtime_config.py`](../src/wolf_325/runtime_config.py), [`async_utils.py`](../src/wolf_325/async_utils.py) | [`test_config_profiles.py`](../tests/test_config_profiles.py), [`test_runtime_configuration.py`](../tests/test_runtime_configuration.py) |
| Store-neutral profile models/engine, file/memory repositories, reusable examples, and capture | [`profile_models.py`](../src/wolf_325/profile_models.py), [`profile_engine.py`](../src/wolf_325/profile_engine.py), [`profiles.py`](../src/wolf_325/profiles.py), [`example_profiles.py`](../src/wolf_325/example_profiles.py), facade in [`controller.py`](../src/wolf_325/controller.py) | [`test_config_profiles.py`](../tests/test_config_profiles.py), [`test_profile_capture.py`](../tests/test_profile_capture.py), [`test_runtime_configuration.py`](../tests/test_runtime_configuration.py) |
| `ValueState`, snapshots, callback and iterator updates | [`state.py`](../src/wolf_325/state.py), [`controller.py`](../src/wolf_325/controller.py) | [`test_controller.py`](../tests/test_controller.py) |
| Client construction, request retries, reconnect generations, and request locking | [`transport.py`](../src/wolf_325/transport.py) | [`test_transport.py`](../tests/test_transport.py), external gateway doubles in [`conftest.py`](../tests/conftest.py) |
| Block/tier polling and availability transitions | [`polling.py`](../src/wolf_325/polling.py) through the [`controller.py`](../src/wolf_325/controller.py) facade | [`test_controller.py`](../tests/test_controller.py), [`test_transport_polling.py`](../tests/test_transport_polling.py), and [`hardware/test_read_all.py`](../tests/hardware/test_read_all.py) |
| Setter helpers, fresh relational preflight, bulk writes, verification, ordering, reconciliation, and resets | [`settings.py`](../src/wolf_325/settings.py), [`setting_relations.py`](../src/wolf_325/setting_relations.py), [`validation.py`](../src/wolf_325/validation.py), [`writes.py`](../src/wolf_325/writes.py) through the [`controller.py`](../src/wolf_325/controller.py) facade | [`test_controller.py`](../tests/test_controller.py), [`test_setting_relations.py`](../tests/test_setting_relations.py), [`test_runtime_edges.py`](../tests/test_runtime_edges.py) |
| `argparse` surface, local profile capture, and device command dispatcher | [`cli_parser.py`](../src/wolf_325/cli_parser.py), [`cli_init.py`](../src/wolf_325/cli_init.py), [`cli.py`](../src/wolf_325/cli.py), [`__main__.py`](../src/wolf_325/__main__.py) | [`test_cli.py`](../tests/test_cli.py), [`test_cli_extended.py`](../tests/test_cli_extended.py) |
| TUI console parser and launch | [`tui.py`](../src/wolf_325/tui.py), `wolf-cwl2-tui` entry in [`pyproject.toml`](../pyproject.toml) | [`test_tui_cli.py`](../tests/test_tui_cli.py) |
| TUI screen composition, lifecycle, mounted-screen-only redraw, selection, and events | [`tui_app.py`](../src/wolf_325/tui_app.py), [`tui.tcss`](../src/wolf_325/tui.tcss) | Mount, interaction, and deterministic post-unmount timer coverage in [`test_tui_app.py`](../tests/test_tui_app.py) |
| Complete catalogue taxonomy and special/domain views | [`tui_navigation.py`](../src/wolf_325/tui_navigation.py), [`tui_views.py`](../src/wolf_325/tui_views.py) | [`test_tui_navigation.py`](../tests/test_tui_navigation.py), [`test_tui_app.py`](../tests/test_tui_app.py) |
| Register rows, search, details, and metadata-derived editors | [`tui_models.py`](../src/wolf_325/tui_models.py) | [`test_tui_models.py`](../tests/test_tui_models.py) |
| Modals, workers, safety guards, profile apply/capture, desired ownership, and controller delegation | [`tui_dialogs.py`](../src/wolf_325/tui_dialogs.py), [`tui_operations.py`](../src/wolf_325/tui_operations.py), [`tui_service.py`](../src/wolf_325/tui_service.py), toolbar/events in [`tui_app.py`](../src/wolf_325/tui_app.py), layout in [`tui.tcss`](../src/wolf_325/tui.tcss) | [`test_tui_service.py`](../tests/test_tui_service.py), [`test_tui_app.py`](../tests/test_tui_app.py) |
| Home Assistant host compatibility baseline | Public [`wolf_325`](../src/wolf_325/__init__.py) imports plus the external HA test host; no component behavior yet | [`test_harness.py`](../tests/components/wolf_cwl2/test_harness.py) |
| Custom-component manifest, translations, domain, and no-I/O lifecycle scaffold | [`custom_components/wolf_cwl2`](../custom_components/wolf_cwl2) | [`test_scaffold.py`](../tests/components/wolf_cwl2/test_scaffold.py) |
| Local HACS repository shape and Home Assistant 2026.3+ brand asset | [`hacs.json`](../hacs.json), [`brand/icon.png`](../custom_components/wolf_cwl2/brand/icon.png), component [`manifest.json`](../custom_components/wolf_cwl2/manifest.json) | Structural coverage in [`test_scaffold.py`](../tests/components/wolf_cwl2/test_scaffold.py), release gates in [`home-assistant-release-validation.md`](workflows/home-assistant-release-validation.md) |
| Per-entry desired, lineage, last-successful profile, portable profiles, revisions, v1-to-v2 Store migration, and removal | [`storage.py`](../custom_components/wolf_cwl2/storage.py), [`storage_models.py`](../custom_components/wolf_cwl2/storage_models.py), [`storage_backend.py`](../custom_components/wolf_cwl2/storage_backend.py), public client profile engine | [`test_storage.py`](../tests/components/wolf_cwl2/test_storage.py), client profile tests |
| Serial identity probe, user/reconfigure config flow, connection schema, policy options, and v1.1-to-v1.2 entry migration | [`probe.py`](../custom_components/wolf_cwl2/probe.py), [`config_flow.py`](../custom_components/wolf_cwl2/config_flow.py), [`config_schema.py`](../custom_components/wolf_cwl2/config_schema.py), [`const.py`](../custom_components/wolf_cwl2/const.py), lifecycle migration in [`__init__.py`](../custom_components/wolf_cwl2/__init__.py) | [`test_probe.py`](../tests/components/wolf_cwl2/test_probe.py), [`test_config_flow.py`](../tests/components/wolf_cwl2/test_config_flow.py), [`test_migrations.py`](../tests/components/wolf_cwl2/test_migrations.py), external gateway fake in [`fakes.py`](../tests/components/wolf_cwl2/fakes.py) |
| Entry runtime, tier deadlines, first refresh, identity verification, availability, entity base, complete read platform, and cleanup | [`__init__.py`](../custom_components/wolf_cwl2/__init__.py), [`entry_config.py`](../custom_components/wolf_cwl2/entry_config.py), [`runtime.py`](../custom_components/wolf_cwl2/runtime.py), [`coordinator.py`](../custom_components/wolf_cwl2/coordinator.py), [`entity.py`](../custom_components/wolf_cwl2/entity.py), [`sensor.py`](../custom_components/wolf_cwl2/sensor.py) | [`test_runtime.py`](../tests/components/wolf_cwl2/test_runtime.py), [`test_coordinator.py`](../tests/components/wolf_cwl2/test_coordinator.py), [`test_sensor.py`](../tests/components/wolf_cwl2/test_sensor.py) |
| Complete HA entity disposition, platform policy, Recorder metadata, safety exclusions, and curated defaults | [`entity_catalogue.py`](../custom_components/wolf_cwl2/entity_catalogue.py), canonical metadata in [`register_catalogue.json`](../src/wolf_325/register_catalogue.json) | [`test_entity_catalogue.py`](../tests/components/wolf_cwl2/test_entity_catalogue.py), contract in [`home-assistant-entities.md`](contracts/home-assistant-entities.md) |
| Authority enforcement, serialized setting mutations, native controls, verified state publication, and translated failures | [`mutations.py`](../custom_components/wolf_cwl2/mutations.py), [`number.py`](../custom_components/wolf_cwl2/number.py), [`select.py`](../custom_components/wolf_cwl2/select.py), [`switch.py`](../custom_components/wolf_cwl2/switch.py), public client [`settings.py`](../src/wolf_325/settings.py) | Happy paths in [`test_controls.py`](../tests/components/wolf_cwl2/test_controls.py), failure/queue/verification/identity/relation paths in [`test_control_failures.py`](../tests/components/wolf_cwl2/test_control_failures.py), lifecycle race guards in [`test_control_lifecycle_guards.py`](../tests/components/wolf_cwl2/test_control_lifecycle_guards.py), contract in [`home-assistant-entities.md`](contracts/home-assistant-entities.md) |
| Persistent active/dormant transitions, explicit resume/clear, reconnect identity gate, drift refresh, and coordinator-owned reconcile cadence | [`coordinator.py`](../custom_components/wolf_cwl2/coordinator.py), [`button.py`](../custom_components/wolf_cwl2/button.py), [`storage.py`](../custom_components/wolf_cwl2/storage.py), [`storage_models.py`](../custom_components/wolf_cwl2/storage_models.py) | [`test_reconciliation.py`](../tests/components/wolf_cwl2/test_reconciliation.py), [`test_coordinator.py`](../tests/components/wolf_cwl2/test_coordinator.py) |
| HA-owned profile options, mode-aware application, persistent lineage, partial-failure queueing, and last-full-success selector truth | [`profile_operations.py`](../custom_components/wolf_cwl2/profile_operations.py), synthetic selector in [`select.py`](../custom_components/wolf_cwl2/select.py), Store adapter in [`storage.py`](../custom_components/wolf_cwl2/storage.py), public engine in [`profile_engine.py`](../src/wolf_325/profile_engine.py) | [`test_profile_application.py`](../tests/components/wolf_cwl2/test_profile_application.py), failure-address support at the external boundary in [`fakes.py`](../tests/components/wolf_cwl2/fakes.py), workflow in [`home-assistant-profiles.md`](workflows/home-assistant-profiles.md) |
| TUI-equivalent HA profile preview/capture action schemas, revision guard, Store commit, and dynamic selector options | [`services.py`](../custom_components/wolf_cwl2/services.py), [`services.yaml`](../custom_components/wolf_cwl2/services.yaml), public capture in [`controller.py`](../src/wolf_325/controller.py) and [`profile_engine.py`](../src/wolf_325/profile_engine.py) | [`test_profile_capture_action.py`](../tests/components/wolf_cwl2/test_profile_capture_action.py), [`test_profile_capture.py`](../tests/test_profile_capture.py) |
| Guarded reset targeting, authority/phrase/option/admin gates, fresh serial verification, dispatch-only appliance semantics, and reconnect invalidation | [`reset_services.py`](../custom_components/wolf_cwl2/reset_services.py), [`service_helpers.py`](../custom_components/wolf_cwl2/service_helpers.py), [`services.yaml`](../custom_components/wolf_cwl2/services.yaml), public reset methods in [`settings.py`](../src/wolf_325/settings.py), reconnect deadlines in [`coordinator.py`](../custom_components/wolf_cwl2/coordinator.py) | [`test_reset_actions.py`](../tests/components/wolf_cwl2/test_reset_actions.py), workflow in [`home-assistant-reset-actions.md`](workflows/home-assistant-reset-actions.md) |
| Identifier-free diagnostics, sanitized Store/setup faults, opaque persistent repairs, resolution, transient-failure exclusion, operation drain, and blocked-entry isolation | [`diagnostics.py`](../custom_components/wolf_cwl2/diagnostics.py), [`repairs.py`](../custom_components/wolf_cwl2/repairs.py), [`storage_errors.py`](../custom_components/wolf_cwl2/storage_errors.py), setup/coordinator ownership in [`__init__.py`](../custom_components/wolf_cwl2/__init__.py) and [`coordinator.py`](../custom_components/wolf_cwl2/coordinator.py), exception sanitation in client [`transport.py`](../src/wolf_325/transport.py) | [`test_diagnostics.py`](../tests/components/wolf_cwl2/test_diagnostics.py), [`test_repairs.py`](../tests/components/wolf_cwl2/test_repairs.py), [`test_runtime.py`](../tests/components/wolf_cwl2/test_runtime.py), [`test_transport.py`](../tests/test_transport.py), workflow in [`home-assistant-diagnostics-and-recovery.md`](workflows/home-assistant-diagnostics-and-recovery.md) |

The reference [`test_wolf_cwl2.py`](../.guides/wolf_cwl2_async/tests/test_wolf_cwl2.py)
is migration evidence for signed temperature decoding, version/serial decoding,
CWL-325 airflow bounds, persisted setter behavior, partial profiles, and
startup write order. It is not sufficient coverage for the package and is not
the package's test suite.

## Data and runtime relationships

- [`register_catalogue.json`](../src/wolf_325/register_catalogue.json) is loaded
  and validated by [`catalogue.py`](../src/wolf_325/catalogue.py). Runtime code
  must not duplicate catalogue values in a second handwritten table. The guide's
  [`REGISTER_MAP.md`](../.guides/wolf_cwl2_async/REGISTER_MAP.md) is descriptive
  migration input, not runtime data.
- A configuration file is loaded by [`config.py`](../src/wolf_325/config.py),
  while embedded hosts inject [`runtime_config.py`](../src/wolf_325/runtime_config.py).
  Its `profiles_dir` selects files consumed by [`profiles.py`](../src/wolf_325/profiles.py),
  and its `state_file` selects snapshots written from [`state.py`](../src/wolf_325/state.py).
- Profile settings and direct setter input pass through the same catalogue
  lookup, normalization, cross-setting validation, and write ordering. Profiles
  must not bypass the normal setter contract.
- [`settings.py`](../src/wolf_325/settings.py) stores the persistently applied
  profile name as `last_profile` and preserves it through later persistent edits
  and releases; this lineage is the parent input for subsequent capture.
- Profile capture travels in the opposite direction: [`controller.py`](../src/wolf_325/controller.py)
  supplies its isolated persistent `desired` mapping and current optional
  `last_profile` to [`profiles.py`](../src/wolf_325/profiles.py). The loader
  resolves the parent, calculates deterministic `settings`/`unset` changes, and
  uses [`config.py`](../src/wolf_325/config.py)'s atomic JSON writer. It does not
  call settings, transport, or polling code and does not update controller
  configuration after saving.
- [`controller.py`](../src/wolf_325/controller.py) coordinates lifecycle only.
  It delegates wire calls to [`transport.py`](../src/wolf_325/transport.py),
  read scheduling to [`polling.py`](../src/wolf_325/polling.py), and writes to
  [`settings.py`](../src/wolf_325/settings.py) and
  [`writes.py`](../src/wolf_325/writes.py).
- The CLI uses the public controller behavior. It must not contain a separate
  implementation of validation, persistence, polling, or raw Modbus access.
- The TUI follows the same rule. [`tui_service.py`](../src/wolf_325/tui_service.py)
  is its only operational adapter: refreshes, writes, ownership release,
  desired-state application, profiles, and one-shot actions call supported
  `WolfCWL2` methods. [`tui_models.py`](../src/wolf_325/tui_models.py) derives
  editor constraints from `RegisterDef` and never maintains a parallel schema.
- [`tui_app.py`](../src/wolf_325/tui_app.py) redraws from isolated controller
  snapshots at the UI interval. Actual device reads remain owned by controller
  polling or explicit refresh actions.
- [`pyproject.toml`](../pyproject.toml) owns author and SPDX license metadata,
  public project URLs, the [`LICENSE`](../LICENSE) inclusion contract, Python
  requirement, base PyModbus dependency, optional `tui` Textual extra,
  development test tools, build backend, client-only wheel/sdist file selection,
  and the `wolf-cwl2` and `wolf-cwl2-tui` entry points that dispatch to
  [`cli.py`](../src/wolf_325/cli.py) and [`tui.py`](../src/wolf_325/tui.py).
  Artifact behavior is verified by [`test_distribution.py`](../tests/test_distribution.py),
  including sdist/wheel license inclusion and published metadata.
- The [`custom_components/wolf_cwl2`](../custom_components/wolf_cwl2) package
  depends only on the public client and Home Assistant. It owns config
  entries, Store adapters, scheduling, entity semantics, and actions; it must
  not duplicate the catalogue or import client-private modules. The Core-shaped
  tests live under [`tests/components/wolf_cwl2`](../tests/components/wolf_cwl2).
- [`manifest.json`](../custom_components/wolf_cwl2/manifest.json) and
  [`.github/CODEOWNERS`](../.github/CODEOWNERS) share the approved
  `@JulianKimmig` owner. The manifest also owns the public documentation and
  issue-tracker URLs; scaffold tests require these values to stay aligned.
- [`README.md`](../README.md) owns user-facing installation and endpoint setup;
  the [device workflow](workflows/physical-device-validation.md) owns repeatable
  live validation and required evidence, while the [TUI workflow](workflows/tui-operation.md)
  owns interactive operation and safety guidance. The [profile capture
  workflow](workflows/profile-capture.md) owns the shared API/CLI/TUI derivation
  and persistence procedure. The [Home Assistant release workflow](workflows/home-assistant-release-validation.md)
  distinguishes locally qualified artifacts from facts and actions that require
  public repository, package-index, or publishing authority.

## Test boundaries

Unit tests may replace the external gateway/client boundary, but must exercise
real package codecs, configuration, profiles, state transitions, controller
ordering, and errors. Tests must not import the guide module or inspect source
text as a substitute for behavior. Physical-device tests are additive: they
prove wire addresses, gateway configuration, optional-device availability, and
real decoding that a simulated client cannot prove. Textual headless tests use
the same external gateway double as controller tests; they must exercise real
presentation, service, controller, validation, and desired-state behavior rather
than replacing package internals. Profile-capture tests use real normalization,
inheritance resolution, and filesystem persistence; CLI/TUI tests verify those
same controller operations through their public operator surfaces.
[`test_profile_capture.py`](../tests/test_profile_capture.py) also exercises the
complete lineage paths: persistently apply a base, persistently edit or release
an inherited key, retain `last_profile`, and save the resulting child
`settings`/`unset` delta.
