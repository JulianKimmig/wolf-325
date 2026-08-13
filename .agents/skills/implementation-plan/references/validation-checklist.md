# Validation Checklist

Run this checklist before final handoff.

## Folder Checks

- The plan lives under `.plan/<plan_name_slug>/`.
- The plan folder is new or explicitly user-approved for update.
- No existing plan folder was overwritten.
- `README.md` records a numeric priority.
- Every generated file is Markdown.
- No product implementation files were changed.
- No YAML, JSON, scripts, images, binaries, or generated code files were created inside the plan folder.

## Required File Checks

- `README.md` exists.
- `00-current-state.md` exists.
- `01-implementation-roadmap.md` exists.
- `02-milestones.md` exists.
- `03-dependencies.md` exists.
- `04-validation-and-risk.md` exists.
- `05-agent-handoff.md` exists.
- `tasks/` exists and contains one Markdown file per implementation task.

## Coverage Checks

- The plan covers the full requested implementation from start to finish.
- All material user-provided details are preserved in `00-current-state.md`, task files, or `appendix-source-requirements.md`.
- User-provided formulas, data layouts, API boundaries, pseudocode, examples, and lifecycle rules are present verbatim or semantically equivalent.
- Known implementation contracts appear in the relevant task files, including applicable file/module boundaries, APIs, data models, state transitions, permissions, workflows, fixtures, and behavioral tests.
- Missing required contract details are recorded as discovery tasks, decision gates, or unresolved-contract notes with dependent later work.
- Explicitly rejected approaches appear under non-goals, risks, stop conditions, acceptance criteria, or `appendix-source-requirements.md`.
- The generated plan can be implemented without access to the original conversation.
- Every in-scope goal maps to at least one milestone or task.
- Explicit non-goals are not planned as implementation tasks.
- Every milestone maps to at least one task.
- Every task maps to exactly one milestone.
- The roadmap explains why tasks are ordered as written.
- Dependencies reference known task IDs.

## Task File Checks

Each task file includes:

- Status.
- Expected current state.
- Source details this task must preserve.
- Implementation contracts and unresolved contract gaps.
- Implementation plan.
- Expected deliverables.
- Acceptance criteria.
- Validation checks.
- Edge cases and risks.
- Completion evidence.
- Stop conditions.

Split any task that lacks a single coherent implementation outcome or validation story.

## Quality Checks

- Early tasks resolve current-state uncertainty and high-risk decisions.
- Early tasks resolve contract uncertainty that would otherwise force implementation agents to redesign APIs, data models, permissions, workflows, or state transitions while coding.
- The plan includes an early thin end-to-end path when relevant.
- Validation includes unhappy paths and not only happy paths.
- Test-first/TDD expectations are included when required by the user or repository.
- Risks are project-specific, not generic filler.
- Commands are not invented. Unknown commands are recorded with discovery steps.
- Dates, budgets, team size, owners, compliance duties, and tool choices are not invented.

## Handoff Checks

- `05-agent-handoff.md` tells future agents what to read first.
- `05-agent-handoff.md` identifies the first recommended task.
- The update protocol says which files to update after a task is completed.
- The replan protocol says when to stop and ask the user.

## Final Response

The final response should include:

- Plan folder path.
- Assigned priority.
- Validation status.
- Number of milestones and task files.
- First recommended task.
- Any blocking unresolved questions.
