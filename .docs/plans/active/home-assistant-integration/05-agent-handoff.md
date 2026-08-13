# Agent Handoff

## Read-First Order

1. Repository `AGENTS.md` and applicable `.rules` retrieved through the
   repository rule-search workflow.
2. [README.md](README.md).
3. [00-current-state.md](00-current-state.md).
4. [appendix-source-requirements.md](appendix-source-requirements.md).
5. [decision-log.md](decision-log.md) and the decision gates in
   [03-dependencies.md](03-dependencies.md).
6. The selected task file and every dependency task's completion evidence.
7. Owning `.docs` architecture/contract/domain/workflow records and relevant
   source/tests named by the task.
8. [research-notes.md](research-notes.md) when a task depends on current Home
   Assistant/HACS behavior.

## How To Choose The Next Task

- Select the lowest-numbered `ready` task whose dependencies are `done`.
- Do not start a task whose decision gate is unresolved.
- If two tasks can run in parallel, assign explicit file/module ownership and
  avoid shared runtime/store/profile files.
- Prefer completing the thin monitoring path through TASK-011 before broad
  entity or mutation work.
- Never treat publication, physical validation, or user decisions as implicitly
  authorized.

## How To Update Statuses

At task start:

- change the task status from `ready`/`not-started` to `in-progress`;
- update the milestone and roadmap current marker;
- record newly discovered applicable rules or contract blockers.

At task completion:

- change the task to `done` only after all acceptance criteria and validation
  checks pass;
- add concise completion evidence, exact tests/checks, commit hash, docs
  updated, and residual risks to the task file;
- update dependent tasks from `not-started` to `ready` when all gates pass;
- update milestone status/exit evidence and this file's current next task;
- update the specific system-of-record entries that own the new facts; and
- make an atomic commit. Never push.

If genuinely blocked, mark the task `blocked`, name the exact external decision
or state change required, and do not weaken acceptance criteria.

## Evidence To Record

- Failing test added before implementation and its intended behavior.
- Focused and regression commands with pass/fail outcomes.
- Relevant task/milestone validation results.
- Public API, schema, entity, storage, migration, or workflow changes.
- Source file line counts and docstring compliance for changed Python modules.
- Sanitized diagnostics/log snapshots where applicable.
- Clean install/version evidence for packaging tasks.
- Physical validation scope, explicit authorization, and redacted results when
  applicable.
- Commit hash and clean `git status` after the closed slice.

## When To Stop And Ask The User

- An immutable domain/model/identity choice is missing or contradicted.
- License, repository, publishing, package, or release authority is required.
- The selected minimum HA/Python/PyModbus combination is incompatible.
- Serial identity is unavailable, unstable, duplicated, or returns a different
  physical appliance during reconfigure/restore.
- A new behavior would broaden physical mutations, dangerous operations,
  profile sharing/import/export, or supported models beyond the plan.
- Date/time, temporary capture, retry suspension, default entity, or counter
  semantics remain unresolved at their gate.
- Completion requires deleting unrelated files, pushing, publishing, or
  altering external systems without explicit authority.
- The one-owner/one-lock or persistence-before-I/O contracts cannot be met
  without a material redesign.

## Replanning Protocol

1. Stop the dependent task before implementation diverges.
2. Record the new evidence in the task and relevant decision entry.
3. Identify affected task IDs, milestones, contracts, and validation gates.
4. Update this active plan without renumbering existing stable IDs; add new task
   IDs only when a coherent new outcome is required.
5. Obtain user approval for scope, safety, external authority, or immutable
   product changes.
6. Resume only after statuses and dependencies reflect the revised path.

When the implementation is genuinely complete, move this plan from
`.docs/plans/active/` to `.docs/plans/completed/` in the same documentation
commit as the final handoff. Do not move it merely because coding paused.

## Current Next Task

- **TASK-001 — Resolve product and release contract gates**
- Status: `ready`
- Reason: every later task depends on at least one immutable, compatibility,
  safety, or release fact owned here.
