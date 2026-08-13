# TASK-020: Complete Documentation, Release, And Physical Validation

## Status

- Status: blocked externally; local deliverables complete
- Milestone: M06
- Dependencies: TASK-007, TASK-019
- Blocks: release and plan completion

## Expected Current State

Implementation behavior is complete, a client artifact exists, and automated
tests pass. Final user/release docs, current external-rule verification,
disposable installation, and read-only physical evidence remain.

## Source Details This Task Must Preserve

- Manual/HACS first, future Core-compatible boundary.
- User docs must explain setup, multiple devices, modes, polling, Recorder,
  defaults/advanced entities, profiles/capture, partial failure, resets,
  diagnostics, recovery, reload/unload/removal.
- Routine physical validation is monitor-only/read-only; writes/profiles/resets
  require separate explicit authorization and recovery evidence.
- Never push from this workflow.

## Implementation Contracts And Gaps

- Manifest pins the exact published lightweight client from TASK-007.
- HACS repository has the approved public metadata, one component directory,
  root `hacs.json`, complete `translations/en.json`, action descriptions,
  README, and required validation workflows.
- Recheck official Home Assistant/HACS rules because research may be stale.
- Physical evidence contains no endpoint, serial, raw live data, credentials, or
  Recorder export.

## Implementation Plan

1. Revisit every official source in `research-notes.md` and update plan/docs for
   changed requirements before release changes.
2. Write documentation/release validation tests/checklists first.
3. Complete README and owning architecture/contracts/domains/workflows,
   including install, operation, profile, safety, diagnostics, recovery,
   release, and physical validation.
4. Finalize manifest exact client pin, component version, HACS metadata,
   translations, action descriptions, and approved public URLs/owners/license.
5. Run wheel/manifest/translation/HACS/hassfest-style checks discovered in
   TASK-002 and the full automated suite.
6. Install manually and through a HACS custom repository in disposable supported
   HA instances; exercise add, duplicate, two entries, options, reconfigure,
   restart, reload, disabled entities, remove, and re-add.
7. With existing device access, run monitor-only physical validation for
   identity, complete mapping, availability, cadence/load, disconnect/reconnect,
   and Recorder/unit behavior. Record only redacted evidence.
8. Create release artifacts only with explicit external authority. Never push.
9. When every gate is genuinely satisfied, record final evidence and move the
   plan to `.docs/plans/completed/` in the closing documentation commit.

## Expected Deliverables

- Complete user/operator/developer/release documentation.
- Valid HACS/manual package using an exact published client.
- Disposable install and read-only physical validation evidence.
- Completed plan handoff and clean committed worktree.

## Acceptance Criteria

- All automated, packaging, translation, HACS/manual install, and lifecycle
  checks pass in supported environments.
- User can understand authority, queued desired state, profile lineage/capture,
  partial application, dangerous guards, and polling/Recorder implications.
- Physical validation performs no mutation and commits no sensitive evidence.
- No release claims an unavailable package, URL, Brands entry, or validation.
- Plan moves to completed only after all required work is done.

## Validation

- Full `uv` suite and exact commands recorded by TASK-002.
- Clean wheel install, exact manifest requirement, component import, manifest,
  translations, HACS/hassfest-style validators.
- Manual/HACS disposable install workflow and redacted monitor-only physical
  checklist.
- `git diff --check`, documentation link audit, clean status after commits.

## Edge Cases And Risks

- HACS/Home Assistant requirements may have changed since plan creation.
- Public repository/Brands/release actions require external permissions.
- One physical appliance cannot validate multi-device hardware identity; retain
  deterministic two-entry tests.
- A physical write can be triggered accidentally if monitor-only defense is
  incomplete; verify request logs and controller read-only guard first.

## Completion Evidence

The current official Home Assistant/HACS sources were rechecked on 2026-08-11.
Local HACS structure, a neutral local brand icon, user/operator/developer/release
documentation, artifact-build regression, and disposable client installation
are complete. Exact artifact sizes, hashes, dependency evidence, and current
publication blockers are recorded in the
[release validation workflow](../../../../workflows/home-assistant-release-validation.md).
The final local completion audit passed `172` standalone tests with `2`
intentional skips and `74` Home Assistant tests, including the expanded
control/profile failure matrix and deterministic TUI teardown regression.

The 2026-08-11 physical recheck was read-only with empty desired state, but the
private gateway was unreachable. It attempted one of 154 definitions, issued no
write, failed both hardware tests, and retained no raw report. The 2026-07-18
successful redacted baseline remains documented separately.

After the gateway address changed, the 2026-08-13 release-day recheck passed
both read-only hardware tests in 15.27 seconds. It accounted for all 154
definitions as 153 available and one unsupported optional, with zero decode
errors, failed keys, or required failures; redacted identity and operational
sanity checks also passed. No physical write was authorized or issued, and the
raw report/config were deleted after recording the aggregate evidence.

HACS/hassfest validation, manual/HACS disposable installation, exact manifest
dependency, and release actions remain blocked by the unpublished client,
initial source push, Trusted Publisher, and release-tag authority. PyPI
`wolf-325`, owned by Julian Kimmig, is the selected production target. The
public repository, documentation/issues URLs, `@JulianKimmig` code owner, and
local `origin` exist; description, issues, and HACS-relevant topics are
configured. Its initial push was not authorized, so it has no default branch
yet. The plan therefore remains active and is not moved to `completed/`.

## Stop Conditions

- Exact client artifact is unpublished/uninstallable.
- Required push/trusted-publisher/release/HACS authority is unavailable.
- Any external publish/push/Brands action lacks explicit authority.
- Physical validation would require a write/profile/reset or expose sensitive
  evidence without separate authorization.
- Any acceptance gate remains incomplete; mark blocked rather than completing.
