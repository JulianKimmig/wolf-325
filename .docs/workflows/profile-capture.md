# Derived profile capture

## Purpose and source state

Capture turns the controller's current persistent desired-state ownership into
a reusable profile document. The source is the canonical `desired` mapping in
the loaded schema-version-1 configuration. It is not a snapshot of live holding
registers or cached values. Consequently, temporary writes and temporarily
applied profiles are excluded because they never enter desired state.

At capture time, `last_profile` is the optional derivation parent. A non-null
name is fully resolved before comparison; `null` produces a standalone profile.
The workflow does not infer a parent from filenames, current device values, or
the most recently previewed profile. Persistently applying a profile sets the
marker; later persistent edits and desired-key releases preserve it. Temporary
changes neither alter desired state nor its parent marker.

## Delta calculation

For a parented capture:

1. Normalize and cross-validate every desired value as restorable state.
2. Resolve the complete parent settings through its inheritance chain.
3. Put desired keys absent from or unequal to the parent in `settings`.
4. Put parent keys absent from desired ownership in `unset`.
5. Copy the parent's resolved `replace` flag.

Keys in `settings` and `unset` are sorted for deterministic output. For a
standalone capture, every desired key is written under `settings`, `unset` is
empty, `replace` is false, and `extends` is omitted. A saved document always
contains `description`, `replace`, `settings`, and `unset`; a parented document
also contains the single-string `extends` name.

The resulting child resolves back to the captured desired mapping while its
parent remains unchanged and resolvable.

## Save guards and side effects

The profile name must match the existing profile-name policy: letters, digits,
`_`, `.`, and `-`, and must be supplied without the `.json` suffix. Capture
rejects invalid names, a missing/malformed/cyclic
parent, self-extension, invalid or non-restorable desired values, and a delta
with neither settings nor unset. Description alone is not a change.

An existing profile name is a collision unless overwrite is explicitly true.
The candidate replacement is resolved as part of the complete catalogue before
commit so an overwritten parent cannot invalidate a descendant. Filesystem
hosts write `<name>.json` with the atomic JSON primitive; embedded hosts use the
same store-neutral engine and return `SavedProfile.path=None`. A successful save
creates or replaces only that profile document. It does not apply or activate
the saved profile, perform Modbus I/O, or change `desired` and `last_profile`.

The Home Assistant `EntryStore` supplies the embedded-host callback over one
versioned per-entry payload. A captured document is visible only after an
immediate Store save and exact readback verification of the next revision. New
Stores seed the canonical examples once; capture and overwrite never cause
examples to be reseeded.

## Python API

`await controller.preview_profile_changes()` returns the `ProfileChanges`
delta without writing and without rejecting an empty preview.

`await controller.save_profile(name, description="", overwrite=False)` applies
all save guards and returns `SavedProfile` containing the target path and exact
delta. Both methods load configuration/profile state when needed and do not
require `controller.start()` or a reachable device.

## CLI

Use the local command:

```bash
uv run wolf-cwl2 \
  --config wolf_cwl2_config.json \
  save-profile custom-night \
  --description "Night profile with local adjustments"
```

Add `--overwrite` only after reviewing the existing target. Successful JSON
output reports the path, parent, replacement policy, releases, and settings.
The normal CLI's `run --read-only` flag belongs to daemon operation and does not
apply to this local command; `save-profile` always performs a profile-file
mutation when its guards pass.

## TUI

In control-enabled mode, use `s` or **Save profile**. The modal previews the
base profile, replacement behavior, persistent settings changes, and released
parent settings before accepting a required name, optional description, and an
overwrite switch that defaults off. Save completion or failure appears through
the normal activity log and notification.

TUI `--read-only` disables the toolbar control and action, and the service
rejects direct save attempts. Preview itself is read-only, but the application
does not expose the capture modal in read-only mode. Saving does not switch the
current profile or alter desired ownership; apply the new profile separately if
that is intended.
