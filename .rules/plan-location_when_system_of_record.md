---
name: plan-location
description: Store repository implementation plans in the .docs system of record if system-of-record is active.
apply: When creating, updating, activating, completing, or handing off implementation plans, execution plans, project plans, task breakdowns, or roadmap artifacts for this repository.
tags: documentation, plans, architecture, system-of-record
visibility: always
---

Create repository implementation plans under `.docs/plans/active/<plan-slug>/`.
Do not create new plan folders under `.plan/`.

Use `.docs/plans/completed/<plan-slug>/` for completed plans. When finishing a
plan-driven implementation, move the plan from `active` to `completed` only
when the implementation is actually complete and the final status, validation,
and handoff notes are updated.
