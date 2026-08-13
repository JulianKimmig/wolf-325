# Agent Handoff

## Read-First Order

1. `README.md`
2. `00-current-state.md`
3. `01-implementation-roadmap.md`
4. `02-milestones.md`
5. `03-dependencies.md`
6. Selected task file in `tasks/`
7. `04-validation-and-risk.md`

## How To Choose The Next Task

Choose the first `ready` or `not-started` task whose dependencies are complete.

## Current Next Task

- Task:
- Reason:

## Update Protocol

After completing a task, update:

- The task file status and completion evidence.
- `01-implementation-roadmap.md` if order changes.
- `02-milestones.md` if milestone status changes.
- `03-dependencies.md` if dependencies change.
- `04-validation-and-risk.md` if risks or validation change.
- This file's current next task.

## Stop And Ask The User When

- Scope or core goals change.
- A dependency cannot be resolved.
- A destructive action is required.
- Production data, credentials, payments, auth, compliance, or security assumptions are unclear.
- A task needs replanning.
