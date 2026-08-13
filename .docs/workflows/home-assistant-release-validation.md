# Home Assistant release validation

## Purpose

This workflow separates reproducible local qualification from external release
facts and actions. It governs the lightweight `wolf-325` artifact, the
`wolf_cwl2` custom component, manual installation, HACS publication, and the
evidence required before claiming an end-user release. Never push or publish as
part of this workflow without explicit authority.

The local integration supports the user-selected contract: multiple serial-
identified entries; configurable fast, slow, static, and reconciliation polling
in seconds; `monitor_only`, `temporary`, and `persistent` authority; all 154
catalogue values classified with curated defaults; Home Assistant-owned
profiles; exact TUI-equivalent persistent capture; and guarded actions instead
of ordinary dangerous entities.

## Current qualification boundary

Local code and tests may be complete while the integration is not installable
by an end user. The component must not claim a manual or HACS release until its
manifest names an exact client version that can be installed from the selected
package index and all required public ownership metadata is approved.

| Gate | Current local state | Release effect |
|---|---|---|
| Client build | `wolf-325` wheel and sdist can be built and installed locally | Necessary, not publication proof |
| Base dependency boundary | Base metadata pins PyModbus; Textual is optional | Qualified by metadata and clean-install tests |
| Component repository shape | One manifest-bearing integration, root `hacs.json`, local icon | Structurally testable before publication |
| Custom translations | Runtime `translations/en.json`; no `strings.json` | Qualified by component tests |
| Public client artifact | PyPI `wolf-325`, owned by Julian Kimmig, selected for production; currently unpublished | Blocks exact manifest requirement until Trusted Publisher release succeeds |
| License and author | MIT; Julian Kimmig is author and copyright holder | Qualified in wheel/sdist metadata tests |
| Public repository metadata | `JulianKimmig/wolf-325`, README documentation, issues, and `@JulianKimmig` owner | Declared in package/component/CODEOWNERS and tested |
| Push/publish authority | Sanitized initial `main` push completed; Trusted Publisher, tag, PyPI, and HACS actions remain separately gated | Blocks remaining external mutation |

The component `manifest.json` contains the approved public documentation,
issue-tracker, and code-owner fields. It intentionally retains an empty
`requirements` list until the exact client artifact is published. Do not
replace that requirement with a local path, editable install, or speculative
version.

The public `JulianKimmig/wolf-325` repository was created on 2026-08-13 with a
description, issues enabled, and the `home-assistant`, `hacs`, `modbus`,
`ventilation`, and `wolf` topics. Its `main` branch was published as a new,
parentless root containing the current source tree. The archival `HA` branch
and its earlier private development history remain local and were not pushed.
Remote verification found only `refs/heads/main`. Public HACS validation still
waits for an exact published client requirement and the remaining release
gates.

The client distribution is licensed under MIT with `Copyright (c) 2026 Julian
Kimmig`; `pyproject.toml` also declares Julian Kimmig as author. Build tests
require the sdist to contain `LICENSE` and the wheel to contain the license text
plus `License-Expression: MIT`, `License-File: LICENSE`, and matching author
metadata.

## Local artifact procedure

Create a fresh output root first; do not validate an existing `dist/` directory
because stale artifacts can carry obsolete metadata:

```bash
mktemp -d /tmp/wolf-325-release.XXXXXX
UV_CACHE_DIR=.cache/uv uv build \
  --out-dir /tmp/wolf-325-release.<generated>/dist
sha256sum /tmp/wolf-325-release.<generated>/dist/wolf_325-*.whl
sha256sum /tmp/wolf-325-release.<generated>/dist/wolf_325-*.tar.gz
```

Create a disposable environment outside the repository and install the exact
wheel path:

```bash
uv venv /tmp/wolf-325-release.<generated>/venv
uv pip install \
  --python /tmp/wolf-325-release.<generated>/venv/bin/python \
  /tmp/wolf-325-release.<generated>/dist/wolf_325-0.1.0-py3-none-any.whl
/tmp/wolf-325-release.<generated>/venv/bin/python -c \
  'import importlib.util, pymodbus, wolf_325; assert importlib.util.find_spec("textual") is None'
```

Use an explicit disposable path and recreate it for each release candidate.
The smoke check must also construct the public runtime configuration and
in-memory repositories without opening a device connection. Record the Python,
client, and PyModbus versions and artifact hashes. Build output under `dist/`
is generated evidence and remains ignored rather than forced into Git.

## Local evidence through 2026-08-13

After applying the selected MIT license and author metadata, the current
checkout produced a 72,809-byte wheel and 56,304-byte sdist from a fresh output
directory. Their SHA-256 values were:

```text
0be0c830fb98c2d3614b31c8daa5e0d1023075a9ff9b08c9daf2ad7bffbf2ded  wheel
dbbdd5280c636925bc13d6e80c58a13e759e38ff525e7a3478c5d7ae064f66f3  sdist
```

The wheel metadata declares author Julian Kimmig, `License-Expression: MIT`,
the included `LICENSE`, all three approved public project URLs, Python 3.11+,
`pymodbus==3.14.0`, and Textual only behind the `tui` extra. The 2026-08-11
installation into a fresh Python 3.13.5
environment installed exactly the client plus PyModbus. Public imports, runtime
configuration, in-memory profile storage, and controller construction worked
from `/tmp`, while Textual remained absent.

The final local completion audit passed 172 standalone client/CLI/TUI tests
with two intentional hardware skips and 74 isolated Home Assistant component
tests. The HA suite includes success, rejection, transport exhaustion,
read-back mismatch, lifecycle race, identity drift, dormant ownership,
relational validation, and partial profile application paths.

An initial release check exposed a stale 2026-07-18 `dist/` wheel and a current
sdist that included repository-local `.cache` and virtual environments. The
build configuration now explicitly limits both artifact targets to the client
package, and `tests/test_distribution.py` rebuilds the sdist and rejects those
host files. The old ignored `dist/` files are not release evidence.

## Component validation procedure

Run the standalone client and isolated Home Assistant suites exactly as
documented in [Home Assistant development](home-assistant-development.md). The
scaffold tests verify the local `hacs.json`, the single component directory,
manifest/translation shape, and square PNG icon. The complete component suite
also covers two-entry lifecycle, options/reconfigure, disabled entities,
authority changes, profiles, guarded actions, reload/unload/removal, Store
migrations, diagnostics, and repairs.

Current upstream requirements must be reviewed immediately before release:

- HACS requires a public GitHub repository, repository metadata, README, and a
  root `hacs.json`.
- HACS integration publication requires one integration under
  `custom_components` and required manifest ownership/support fields.
- Custom components use `translations/en.json`, not Core's build-time
  `strings.json`.
- Home Assistant 2026.3 and newer can consume local custom-integration brand
  assets from `brand/`; older hosts may not display them.

After public metadata and an exact published client exist, add tests for the
exact manifest fields first, then update the manifest. Run the current HACS and
hassfest validators against the public repository. A local structural test is
not a substitute for those external validators.

## Disposable manual and HACS install matrix

Only execute this matrix after the exact manifest dependency is installable.
Use a supported clean Home Assistant instance with no repository checkout on
its Python path.

1. Manually copy only `custom_components/wolf_cwl2`, restart, add one entry,
   verify default entities and Recorder updates, reload, remove, and re-add.
2. Add the approved public repository as a HACS custom integration, install,
   restart, and repeat the same lifecycle without local-path assistance.
3. Add two distinct serial-backed entries, verify isolation, change polling and
   authority options independently, reconfigure one endpoint, and restart.
4. Enable representative default-disabled entities and confirm stable IDs,
   availability, units, and Recorder behavior.
5. Exercise profile selection, preview, capture, overwrite/revision conflicts,
   persistent resume/clear, partial failures, and guarded reset rejection paths.
6. Download diagnostics and verify that no endpoint, serial, values, desired
   state, profile content, or raw exception text is present.

Do not use a production Home Assistant database for release qualification.
Reset actions should be validated through rejection paths unless a separate
physical-write workflow is explicitly authorized.

## Physical evidence boundary

Release validation may reuse the read-only catalogue audit in
[physical device validation](physical-device-validation.md). It may confirm
identity decoding, complete address coverage, supported/optional availability,
and plausible live values. It must not apply a profile, restore desired state,
write a control, or reset the appliance.

A single appliance cannot prove multi-device physical isolation, HACS install,
Recorder persistence, or disconnect/reconnect behavior. Those remain automated
or disposable-host gates unless additional safe infrastructure is explicitly
authorized. Store only aggregate, redacted physical evidence in this workflow.

The release-day read-only gate was rerun on 2026-08-13 after the private gateway
address changed. Both hardware tests passed in 15.27 seconds with empty desired
state, unit 20, and offset 0: all 154 catalogue definitions were classified as
153 available and one unsupported optional, with no decode errors, failed keys,
or required failures. Identity shape and operational-value plausibility checks
passed. The raw report and disposable config were deleted; no endpoint, serial,
or live value was retained here and no write was issued.

## Release completion criteria

A release is complete only when all of these are true:

- approved license, owner, support, and public URLs are present;
- the exact client version is published and clean-index-installable;
- the component manifest pins that exact version;
- current HACS/hassfest validation passes against the public repository;
- manual and HACS disposable install matrices pass;
- automated client and component suites pass;
- the read-only physical catalogue gate passes without sensitive evidence; and
- explicit authority exists for each push, tag, package upload, and HACS
  submission.

If any item is absent, record the local evidence and blocker without calling
the integration released or moving its implementation plan to completed.
