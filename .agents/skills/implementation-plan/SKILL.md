---
name: implementation-plan
description: Create a detailed Markdown-only implementation plan from a product, project, feature, or technical description. Use when the user asks for an implementation plan, project plan, milestone breakdown, delivery plan, work packages, task-by-task implementation steps, dependencies, validation plan, risk register, or handoff instructions for future coding agents. The skill creates a new `.plan/plan-name-slug/` folder containing only Markdown files, with separate implementation task files from start to finish. Do not use for immediate coding unless the user asks to implement after planning.
---

# Implementation Plan

## Overview

Create a durable Markdown-only implementation plan folder under `.plan/<plan_name_slug>/`. The plan must preserve the expected current state, ordered implementation path, task-level deliverables, validation gates, risks, source requirements, and handoff rules so future agents can implement the project without reconstructing the original conversation.

## Source Preservation Rules

Before decomposing the plan, extract a source-retention ledger from the user request. The generated plan must preserve all material information from the request in explicit Markdown:

- Current behavior and target behavior.
- User interaction requirements.
- Performance constraints and anti-patterns.
- Architecture requirements and ownership boundaries.
- Implementation-critical details such as formulas, data layouts, protocols, lifecycle rules, configuration, API contracts, pseudocode, or supplied examples.
- Concrete implementation contracts when present, including shared module/file boundaries, APIs, data models, data flows, permissions, migrations, state transitions, workflow steps, fixtures, and behavioral test expectations.
- Rationale for preferred and rejected approaches.
- Explicit non-goals and forbidden implementations.

Do not compress dense design context into a one-sentence summary. If the request contains detailed product, technical, performance, architecture, API, formula, or rationale content that would be lossy if summarized in `README.md`, create `appendix-source-requirements.md` and reference it from `README.md`, `00-current-state.md`, relevant task files, and validation/risk planning.

A future implementation agent must not need the original conversation to recover design intent, constraints, or implementation-critical details.

## Workflow

1. Confirm the request is for planning, not immediate implementation. If the user asks to implement directly and does not want a plan folder, do not use this skill.
2. Inspect the product/project description and relevant local repository context when available. Read local instructions, existing docs, tests, package files, source layout, and prior `.plan/` folders if they affect the plan.
3. Ask only blocking clarification questions. If the plan can proceed responsibly, record assumptions instead of pausing.
4. Extract a source-retention ledger from the request. Decide whether the plan needs `appendix-source-requirements.md`; create it whenever source detail would be lost by only summarizing in top-level files.
5. Read [references/planning-rubric.md](references/planning-rubric.md) before decomposing the work.
6. Read [references/file-contract.md](references/file-contract.md) before creating files.
7. Use web research only when the user requests it or current external facts materially affect the plan. If web research is used, first read [references/web-research-guidance.md](references/web-research-guidance.md).
8. Assign the new plan a priority number. Use the priority the user requested when one is specified; otherwise use `9`. Priority `1` is highest priority; larger numbers are lower priority. Record the priority in `README.md` under Plan Identity.
9. Create one new `.plan/<plan_name_slug>/` folder. Generate a lowercase hyphen slug from the project name or concise inferred title. If the folder exists, append `-2`, `-3`, etc.; never overwrite or merge with an existing plan folder unless the user explicitly asks for an update.
10. Write only Markdown files inside the plan folder. Do not create YAML, JSON, scripts, images, generated code, or product implementation files as part of this skill.
11. Create the required plan files and one separate Markdown task file per implementation task. Use the templates in `assets/templates/` as structural guidance when useful.
12. Validate the completed plan with [references/validation-checklist.md](references/validation-checklist.md).
13. Reply with the plan folder path, assigned priority, validation status, unresolved blocking questions if any, and the first recommended implementation task.

## Required Plan Output

Every generated plan must live under:

```text
.plan/<plan_name_slug>/
```

Required Markdown files:

```text
README.md
00-current-state.md
01-implementation-roadmap.md
02-milestones.md
03-dependencies.md
04-validation-and-risk.md
05-agent-handoff.md
tasks/task-001-<task-slug>.md
tasks/task-002-<task-slug>.md
...
```

Add optional Markdown files only when they materially improve execution, such as `research-notes.md`, `decision-log.md`, or `appendix-domain-notes.md`.

Create `appendix-source-requirements.md` when the source request contains dense details that future agents must preserve exactly or near-exactly. Use it for implementation-critical details, architecture rationale, formulas, protocols, anti-patterns, examples, or boundary rules that would be weakened by summary.

Every generated plan must include a numeric priority in `README.md` Plan Identity. If the user did not request a priority, set it to `9`. Priority `1` is highest priority; larger numbers are lower priority.

## Task File Requirements

Each `tasks/task-NNN-<task-slug>.md` file must be executable by a future implementation agent and include:

- Task ID, title, milestone, status, and dependencies.
- Expected current state before the task starts.
- Source details this task must preserve.
- Implementation contracts and unresolved contract gaps. Include known APIs, data models, boundaries, permissions, migrations, workflows, state transitions, fixtures, and behavioral test expectations that affect this task. If required contract details are missing, name the unresolved categories, add discovery or decision work, and identify dependent later tasks.
- Implementation plan for that task.
- Expected deliverables after the task is complete.
- Acceptance criteria and validation checks.
- Edge cases and risks.
- Completion evidence to record.
- Stop conditions that require user input or replanning.

Split tasks until each file has one coherent implementation outcome and one validation story. If a task has unrelated deliverables or validation paths, split it into multiple task files.

## Planning Rules

- Decompose by deliverables first, then sequence by dependencies, risk reduction, and user value.
- Preserve source details before compressing them into tasks. Summaries may be concise, but they must not drop constraints, rationale, anti-patterns, formulas, APIs, boundary rules, or user-visible behavior.
- Put discovery, baseline verification, test setup, and high-risk technical decisions early when they unblock later work.
- Prefer a thin end-to-end path before broad horizontal buildout.
- Do not ask implementation agents to redefine core contracts when the source request already provides them. Place known contract details directly in the affected task files. When contract details are required but absent, add discovery tasks, decision gates, or "to resolve before implementation" notes instead of fabricating specificity.
- Do not invent dates, staffing, budgets, technology choices, compliance requirements, or commands. If unknown, record the gap and add a discovery task or decision gate.
- Include TDD/test-first expectations when the user or repository instructions require them.
- Keep generated content practical for implementation agents, not just project stakeholders.

## Final Checks

Before final response, verify:

- The `.plan/<plan_name_slug>/` folder is new and was not overwritten.
- `README.md` records the assigned priority.
- All generated files are Markdown files.
- The roadmap covers the full requested implementation from start to finish.
- The plan preserves all material source details in `00-current-state.md`, task files, or `appendix-source-requirements.md`.
- User-provided formulas, data layouts, API boundaries, pseudocode, examples, and rejected approaches are present verbatim or semantically equivalent.
- Task files include known implementation contracts or explicitly name unresolved contract categories and dependent work.
- Every milestone maps to at least one task file.
- Every task file includes expected current state, implementation plan, expected deliverables, validation checks, and completion evidence.
- Dependencies are explicit and refer to known task IDs.
- Risks, assumptions, and unresolved questions are captured.
- `05-agent-handoff.md` identifies the first recommended task and the update protocol for future agents.
