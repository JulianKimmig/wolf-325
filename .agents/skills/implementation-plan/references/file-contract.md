# Markdown File Contract

Generated output must be Markdown-only and must live inside one `.plan/<plan_name_slug>/` folder.

Every new plan must be assigned a numeric priority. Use the priority number the user requested when one is specified; otherwise use `9`. Priority `1` is highest priority; larger numbers are lower priority. Record the priority in `README.md` under Plan Identity.

## Folder Naming

Use this default root:

```text
.plan/
```

Create a plan folder:

```text
.plan/<plan_name_slug>/
```

Slug rules:

- Lowercase ASCII.
- Hyphen-separated.
- Derived from the project name or concise inferred title.
- Maximum practical length: 48 characters.
- If the folder exists, append `-2`, `-3`, etc.
- Never overwrite, delete, or merge an existing plan folder unless the user explicitly requests update mode.

## Required Layout

```text
.plan/<plan_name_slug>/
├── README.md
├── 00-current-state.md
├── 01-implementation-roadmap.md
├── 02-milestones.md
├── 03-dependencies.md
├── 04-validation-and-risk.md
├── 05-agent-handoff.md
└── tasks/
    ├── task-001-<task-slug>.md
    ├── task-002-<task-slug>.md
    └── ...
```

Optional Markdown files:

- `research-notes.md` when web or external documentation was used.
- `decision-log.md` for complex tool, architecture, or scope decisions.
- `appendix-source-requirements.md` when the user request includes detailed product, technical, performance, architecture, API, formula, example, or rationale content that would be lossy if summarized in `README.md`.
- `appendix-<topic>.md` for large non-executable context.

Do not generate non-Markdown files.

## Top-Level File Roles

### `README.md`

Entry point and navigation map.

Required sections:

- Plan identity.
- Assigned priority.
- Source request summary.
- Source detail location, pointing to `appendix-source-requirements.md` when created.
- How to use this plan.
- File map.
- First recommended task.
- Current status.

### `00-current-state.md`

Expected current state before implementation starts.

Required sections:

- Product/project interpretation.
- Existing repository or system state.
- Source-derived requirements.
- Source-derived constraints.
- Forbidden or rejected approaches.
- Design rationale to preserve.
- User goals and success criteria.
- Scope and non-scope.
- Constraints and instructions.
- Assumptions.
- Unknowns.

### `01-implementation-roadmap.md`

Start-to-finish implementation sequence.

Required sections:

- Roadmap summary.
- Full ordered sequence.
- Sequencing rationale.
- Thin end-to-end path.
- Parallelization opportunities.
- Replanning checkpoints.

### `02-milestones.md`

Milestone plan.

Required sections:

- Milestone overview table.
- One section per milestone.
- Entry criteria.
- Exit criteria.
- Deliverables.
- Validation gates.
- Related task IDs.

### `03-dependencies.md`

Dependency map.

Required sections:

- Task dependency table.
- Milestone dependency table.
- Critical path.
- External dependencies.
- Decision gates.
- Blocking questions.

### `04-validation-and-risk.md`

Quality, validation, and risk plan.

Required sections:

- Test strategy.
- Task validation rules.
- Milestone validation rules.
- Final acceptance checks.
- Risk register.
- Security/privacy/data checks when relevant.
- Release or handoff checks.

### `05-agent-handoff.md`

Instructions for future implementation agents.

Required sections:

- Read-first order.
- How to choose the next task.
- How to update statuses.
- What evidence to record.
- When to stop and ask the user.
- Replanning protocol.
- Current next task.

### `appendix-source-requirements.md`

Non-lossy source request preservation for dense user requests.

Required sections when created:

- Original request digest.
- Current behavior.
- Target behavior.
- User interaction requirements.
- Architecture and ownership boundaries.
- Performance requirements.
- Implementation-critical details.
- Rejected approaches.
- Rationale.
- Traceability.

## Task File Contract

Each task file must use this structure:

```markdown
# TASK-001: <Task Title>

## Status

- Status:
- Milestone:
- Dependencies:
- Blocks:

## Expected Current State

Describe what should be true before this task starts.

## Source Details This Task Must Preserve

List the specific source request details this task implements or protects.

## Implementation Contracts And Gaps

List concrete contracts this task must preserve or create, such as expected
files/modules, APIs, data models, request/response shapes, state transitions,
permissions, migrations, workflows, fixtures, and behavioral test expectations.
If required contract details are unknown, name the unresolved categories, add
discovery or decision work, and identify dependent later tasks.

## Implementation Plan

Describe the concrete implementation steps for this task.

## Expected Deliverables

List what should exist after the task is complete.

## Acceptance Criteria

List observable acceptance criteria.

## Validation

List tests, commands, manual checks, or discovery steps.

## Edge Cases And Risks

List task-specific risks and edge cases.

## Completion Evidence

State what the implementation agent must record when done.

## Stop Conditions

List conditions requiring user input or replanning.
```

## ID Conventions

- Tasks: `TASK-001`, `TASK-002`, `TASK-003`
- Milestones: `M01`, `M02`, `M03`
- Risks: `RISK-001`, `RISK-002`
- Decisions: `DEC-001`, `DEC-002`
- Questions: `Q-001`, `Q-002`

IDs must be stable. Do not renumber IDs after creating the plan.

## Status Values

Use these status values:

- `not-started`
- `ready`
- `in-progress`
- `blocked`
- `done`
- `deferred`
- `needs-replan`

Every task starts as `not-started` or `ready`.
