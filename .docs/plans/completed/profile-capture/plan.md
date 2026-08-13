# Derived profile capture plan

## Objective

Allow operators to save the current persistent desired-state changes as a new
profile from both `wolf-cwl2` and `wolf-cwl2-tui`. When a profile is currently
loaded (`last_profile`), the new document extends it and stores only the delta.

## Behavioral contract

- Resolve the loaded profile before calculating changes.
- Store desired values that are new or differ from the resolved parent under
  `settings`.
- Store parent settings absent from desired state under `unset`.
- Preserve the parent profile's `replace` behavior.
- Without a loaded profile, save the complete desired state as a standalone
  partial profile.
- Reject invalid names, self-extension, empty captures, and existing targets
  unless overwrite is explicitly requested.
- Write JSON atomically and do not change the active profile or desired state.
- Temporary writes are not captured because they are not durable desired state.

## Surfaces

- Public controller methods preview and save the derived profile.
- CLI command: `save-profile NAME [--description TEXT] [--overwrite]`.
- TUI toolbar/key action opens a dialog showing the base and delta summary,
  then accepts name, description, and explicit overwrite selection.

## Verification

- Pure profile-capture tests cover inheritance, settings/unset deltas,
  standalone capture, replacement policy, validation, collisions, and loading
  the saved result.
- CLI tests cover parser and local no-device dispatch.
- Headless TUI tests cover dialog submission and read-only disabling.
- Full suite, package build, line limits, and system-of-record records are
  verified before completion.

## Completion evidence

- Pure capture tests verify inherited and standalone deltas, `settings`,
  `unset`, `replace`, round-trip resolution, empty/self/name/suffix guards,
  collisions, and explicit overwrite.
- Real controller tests verify apply-base → persistent edit/release → save
  child while retaining parent lineage.
- CLI tests verify parser, JSON result, local-only execution, and unchanged
  desired/active-profile state.
- Headless TUI tests verify read-only disabling and dialog-driven child save.
- The full suite passes with 159 tests and two opt-in hardware tests skipped;
  source and wheel builds succeed and every source module remains below 300
  lines.
