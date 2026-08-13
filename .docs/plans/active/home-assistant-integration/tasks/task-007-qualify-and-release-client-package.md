# TASK-007: Qualify And Release The Client Package

## Status

- Status: blocked externally; local artifact qualification complete
- Milestone: M02
- Dependencies: TASK-006
- Blocks: TASK-020 and the final exact manifest requirement

## Expected Current State

The client is lightweight and buildable locally. Public repository/package
ownership, license metadata, project URLs, and release version are approved by
TASK-001, or this task is externally blocked.

## Source Details This Task Must Preserve

- HACS component depends on an exact released client artifact.
- Do not vendor client code or install Textual into Home Assistant.
- Never push or publish without explicit external authority.

## Implementation Contracts And Gaps

- Package metadata includes approved license, owners, URLs, Python range, and
  version.
- Exact PyModbus pin/range is qualified against the selected minimum/current HA
  environments.
- Wheel/sdist install base client only; TUI remains optional.
- Manifest requirement is not finalized until the artifact is actually
  installable.

## Implementation Plan

1. Verify external release authority and approved metadata; otherwise mark the
   task blocked without publishing.
2. Write package/build/import/install tests before metadata changes.
3. Build wheel/sdist with the repository's discovered `uv` workflow.
4. Install into clean selected HA/Python environments and test base import,
   direct construction, PyModbus import, and absence of Textual.
5. Qualify the exact dependency version used by the integration tests.
6. With explicit authority, publish/release the client and verify index
   installation by exact version.
7. Record artifact hashes/URLs/version and make them available to TASK-020.

## Expected Deliverables

- Qualified client artifacts and reproducible install evidence.
- Published exact version if authorized.
- Approved package metadata and release workflow documentation.

## Acceptance Criteria

- Clean supported environments install and import the exact artifact.
- No unpublished/local path appears in the release manifest contract.
- Textual is absent from the base installation.
- Artifact metadata matches approved compatibility and license facts.

## Validation

- Build metadata checks, clean environment install, package import, controller
  smoke test, dependency inspection, and full client suite.
- Verify released artifact hash/version from the target package index when
  publishing is authorized.

## Edge Cases And Risks

- Home Assistant and client may require incompatible PyModbus versions.
- Publishing name/version ownership may be unavailable.
- A release cannot be replaced safely once referenced.

## Completion Evidence

On 2026-08-13 `uv build` created the licensed 72,809-byte wheel and 56,304-byte
sdist in a fresh disposable output directory. Current SHA-256 values are
recorded in the [release validation workflow](../../../../workflows/home-assistant-release-validation.md).
A clean Python 3.13.5 environment installed `wolf-325==0.1.0` with
`pymodbus==3.14.0`, without Textual, and passed public import/direct-construction
smoke checks. The behavioral sdist regression rejects repository caches and
host-adapter sources.

MIT licensing and Julian Kimmig author/copyright metadata were accepted on
2026-08-13. Behavioral builds prove the sdist contains `LICENSE` and the wheel
publishes `License-Expression: MIT`, `License-File: LICENSE`, and the selected
author. Public project URLs and `@JulianKimmig` code ownership are now declared
in package/component metadata and behavioral tests. PyPI project `wolf-325`,
owned by Julian Kimmig, is the selected production target; its JSON API returned
404 before initial publication. Publication remains blocked until the source is
pushed and a matching Trusted Publisher/release tag is authorized and
configured. No artifact was uploaded, tagged, pushed, or referenced from the
component manifest.

## Stop Conditions

- Initial source push, Trusted Publisher, or release-tag authority is unresolved.
- Selected HA environment conflicts with the client dependency.
- Exact artifact installation fails; do not proceed with a release manifest pin.
