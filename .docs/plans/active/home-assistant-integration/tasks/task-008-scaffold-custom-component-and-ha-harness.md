# TASK-008: Scaffold Custom Component And Home Assistant Harness

## Status

- Status: done locally; publication metadata remains externally blocked
- Milestone: M03
- Dependencies: TASK-001, TASK-002, TASK-006
- Blocks: TASK-009–013

## Expected Current State

The client is HA-safe and the HA test baseline exists. No
`custom_components/<domain>/`, HACS metadata, component manifest, translations,
or platform lifecycle exists.

## Source Details This Task Must Preserve

- Manual/HACS native integration, one integration directory, future Core shape.
- Complete `translations/en.json`; no custom-component `strings.json`.
- Source modules below 300 lines and detailed docstrings.

## Implementation Contracts And Gaps

- Directory matches approved immutable domain.
- `manifest.json` uses approved name/version/codeowners/docs/issues,
  `config_flow: true`, `iot_class: local_polling`, `integration_type: device`,
  and a development requirement strategy that becomes an exact released pin.
- `hacs.json` is at repository root with approved minimum HA metadata.
- Typed `ConfigEntry.runtime_data` alias and platform list are stable.

## Implementation Plan

1. Write failing structure/import/translation/manifest tests in the Core-shaped
   HA test tree.
2. Add minimal component package, constants/types, `async_setup`, setup-entry /
   unload stubs that do not yet open the device, and full English translation
   skeleton.
3. Add root HACS metadata and action description file only when corresponding
   actions exist; avoid placeholder product claims.
4. Add manifest development requirement handling without pinning an unpublished
   artifact as release-ready.
5. Validate one integration directory and clean custom-integration loading.
6. Update architecture and code-relationship records with actual files.

## Expected Deliverables

- Loadable custom-component skeleton and HACS metadata.
- Core-shaped component tests and translations.
- Typed integration-domain boundaries.

## Acceptance Criteria

- Component imports/loads in the chosen HA test host.
- Manifest and translations validate.
- No `strings.json`, vendored controller, duplicate wire schema, or device I/O
  exists in the scaffold.
- All runtime integration files reside under the component directory.

## Validation

- HA custom-integration load test, manifest/translation validation, package
  import, file layout audit, full client regression.
- LOC/docstring and `git diff --check` checks.

## Edge Cases And Risks

- HACS requires public metadata not available during local development.
- Component version and client version are distinct.
- An early manifest pin can point to a nonexistent artifact.

## Completion Evidence

`custom_components/wolf_cwl2` now provides the immutable domain, local
manifest, custom `translations/en.json`, versioned config-flow declaration, and
no-I/O config-entry load/unload lifecycle. HA-only tests validate exact
structure, absence of `strings.json`, and lifecycle behavior. Root HACS
metadata, brand assets, the public repository/documentation/issue URLs, and
`@JulianKimmig` code ownership are present and tested. Only the exact published
client requirement remains intentionally absent until TASK-007 publication is
authorized and verified. Commit hash is recorded after this closed slice.

## Stop Conditions

- Immutable domain or required manifest metadata is unresolved.
- Scaffolding requires vendoring or importing private client modules.
- Selected HA version rejects the proposed component structure.
