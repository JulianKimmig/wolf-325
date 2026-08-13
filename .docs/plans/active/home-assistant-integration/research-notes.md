# Research Notes

## Research Questions

- What current Home Assistant coordinator, polling, entity, Recorder, config
  flow, options, action, diagnostics, and localization rules affect the plan?
- What current manifest and HACS repository requirements block distribution?

All sources were accessed on **2026-08-11** and the release-sensitive sources
were rechecked on that date during TASK-020. Recheck them again immediately
before any later publication because these platform facts can change.

## Sources

### SRC-001: Fetching Data

- URL: https://developers.home-assistant.io/docs/integration_fetching_data/
- Summary: Coordinated polling should use `DataUpdateCoordinator`; polling only
  runs while it has subscribers, comparable data can use `always_update=False`,
  entity properties read memory, and the minimum polling interval is five
  seconds.
- Plan impact: TASK-011 retains an entry-lifetime scheduler/listener, uses one
  coordinator owner, excludes volatile equality data, and validates intervals.
- Staleness risk: high; coordinator lifecycle APIs evolve.

### SRC-002: Integration Manifest

- URL: https://developers.home-assistant.io/docs/creating_integration_manifest/
- Summary: The manifest domain is immutable and directory-matching; custom
  integrations require a version; config flow, `iot_class`, integration type,
  code owners, documentation, issue tracker, and exact Python requirements are
  declared here.
- Plan impact: TASK-001, TASK-008, TASK-020.
- Staleness risk: high.

### SRC-003: Custom Integration Localization

- URL: https://developers.home-assistant.io/docs/internationalization/custom_integration/
- Summary: Custom integrations must ship complete `translations/en.json` and
  must not rely on Core's build-time `strings.json` or placeholders.
- Plan impact: TASK-008 and TASK-020.
- Staleness risk: high; guidance changed recently.

### SRC-003A: Custom Integration Brand Assets

- URL: https://developers.home-assistant.io/docs/core/integration/brand_images/
- Summary: Home Assistant 2026.3 and newer allow custom integrations to ship
  local brand assets under the integration's `brand/` directory. Earlier Home
  Assistant releases depended on the external Brands repository for equivalent
  frontend assets.
- Plan impact: TASK-020 adds a neutral local icon, but the currently locked
  2026.2.3 test host remains the behavioral compatibility floor and therefore
  does not prove local-icon rendering.
- Staleness risk: high; this capability changed in 2026.3.

### SRC-004: Config Flow

- URL: https://developers.home-assistant.io/docs/core/integration/config_flow/
- Summary: Stable unique IDs must not use IP addresses; serial numbers are an
  acceptable source. Reconfigure should update/reload the existing entry and
  reject a unique-ID mismatch.
- Plan impact: TASK-009 and identity tests in TASK-011.
- Staleness risk: medium.

### SRC-005: Options Flow

- URL: https://developers.home-assistant.io/docs/core/integration/options_flow/
- Summary: `OptionsFlowWithReload` automatically reloads changed options and
  avoids needing a second update listener for the same purpose.
- Plan impact: TASK-009 uses one reload mechanism and tests exactly one reload.
- Staleness risk: medium.

### SRC-006: Entity Contract

- URL: https://developers.home-assistant.io/docs/core/entity/
- Summary: Unique IDs are stable and non-user-configurable; translated names are
  preferred; default-disabled entities reduce clutter; forced updates and
  changing attributes can inflate Recorder; entity properties must be stable.
- Plan impact: TASK-012 and TASK-013.
- Staleness risk: medium.

### SRC-007: Sensor And Long-Term Statistics

- URL: https://developers.home-assistant.io/docs/core/entity/sensor/
- Summary: Long-term statistics require legal `MEASUREMENT`, `TOTAL`, or
  `TOTAL_INCREASING` semantics and compatible device classes/units. Total
  behavior must reflect actual reset/monotonic behavior.
- Plan impact: TASK-012, TASK-013, and physical validation in TASK-020.
- Staleness risk: medium.

### SRC-008: Action Failure Semantics

- URL: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/action-exceptions/
- Summary: Misuse should raise `ServiceValidationError`; runtime/network/action
  failures should raise `HomeAssistantError`; this also applies to entity
  actions.
- Plan impact: TASK-014, TASK-016–018.
- Staleness risk: medium.

### SRC-009: Integration Diagnostics

- URL: https://developers.home-assistant.io/docs/core/integration/diagnostics/
- Summary: Config-entry/device diagnostics are downloadable and sensitive data
  must be removed; `async_redact_data` is available.
- Plan impact: TASK-019, with client log sanitation as an additional layer.
- Staleness risk: medium.

### SRC-010: Config Entries

- URL: https://developers.home-assistant.io/docs/config_entries_index/
- Summary: Config entries have explicit setup/retry/unload/remove lifecycle;
  forwarded platforms must unload; schema version changes require migration;
  integrations must use supported update helpers.
- Plan impact: TASK-009–011 and TASK-019.
- Staleness risk: medium.

### SRC-011: HACS Integration Repository Requirements

- URL: https://hacs.xyz/docs/publish/integration/
- Summary: One integration directory belongs under `custom_components`; all
  runtime files live there. The manifest must include `domain`, `documentation`,
  `issue_tracker`, `codeowners`, `name`, and `version`. A local `brand/icon.png`
  is required by the current integration publication checklist.
- Plan impact: TASK-008 and TASK-020.
- Staleness risk: high.

### SRC-012: HACS General Publication Requirements

- URL: https://hacs.xyz/docs/publish/start/
- Summary: HACS publication requires a public GitHub repository, README,
  root-level `hacs.json`, repository description/topics, and release
  discipline. These requirements cannot be truthfully validated against a
  repository without an approved public remote.
- Plan impact: TASK-001, TASK-007, TASK-020.
- Staleness risk: high.

### SRC-013: Home Assistant Store Serialization Change

- URL: https://developers.home-assistant.io/blog/2025/11/25/storage-helper-opt-in-serialize-in-executor/
- Summary: Store serialization threading behavior is configurable/currently
  version-dependent; data passed to Store must remain JSON-safe and thread-safe
  when off-loop serialization is selected.
- Plan impact: TASK-010 must qualify the selected minimum HA version and test
  immediate durable save behavior instead of assuming old Store threading.
- Staleness risk: high.

### SRC-014: Hatch Build File Selection

- URL: https://hatch.pypa.io/1.10/config/build/
- Summary: Hatch build targets support explicit `include` and `packages` file
  selection. Without target selection, an sdist can traverse repository files
  that are not ignored by the active VCS view.
- Plan impact: TASK-007 and TASK-020 explicitly limit the client wheel/sdist to
  `src/wolf_325` and behavior-test the generated sdist.
- Staleness risk: low; this is the selected build backend's public contract.
