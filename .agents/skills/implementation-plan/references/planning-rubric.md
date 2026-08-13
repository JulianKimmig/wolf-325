# Planning Rubric

Use this rubric to turn a product, project, feature, or technical description into an implementation plan that future agents can execute.

## Intake

Extract and record:

- Project or feature name.
- User groups and stakeholders.
- Product goal and success criteria.
- In-scope deliverables.
- Non-goals and excluded paths.
- Repository, platform, package manager, framework, deployment, and test constraints.
- Security, privacy, data, compliance, migration, integration, or production risks.
- Current state expected before implementation starts.
- Implementation-critical details such as formulas, data layouts, protocols, lifecycle rules, configuration, API contracts, pseudocode, or supplied examples.
- Explicitly rejected approaches, anti-patterns, and performance traps.
- Architecture, ownership, interaction, and boundary rules.
- Concrete implementation contracts, including shared file/module boundaries, APIs, data models, state machines, permissions, migrations, workflows, fixtures, and behavioral test expectations.
- Rationale the user provided for preferred or rejected approaches.
- Unknowns and assumptions.

Classify unknowns as:

- Blocking: the plan would be materially wrong without an answer.
- Assumable: proceed with an explicit assumption and revisit trigger.
- Watchlist: track during implementation but do not block planning.

Ask at most a small set of blocking questions. Otherwise produce a provisional plan with explicit assumptions.

## Source Retention

Before summarizing or decomposing the request, preserve material source details in a source-retention ledger. Use `appendix-source-requirements.md` when the request includes dense details that future implementation agents need to recover without reading the original conversation.

The plan must not lose:

- Concrete current-state and target-state behavior.
- User interaction flows and user-visible constraints.
- Performance requirements and forbidden implementation strategies.
- Architecture and ownership boundaries.
- Implementation-critical details, examples, formulas, pseudocode, contracts, and lifecycle rules.
- Concrete contract details in the task files that will implement or protect them, not only in an appendix or overview.
- Rationale for why an approach is required or rejected.

Every material source detail must appear in at least one executable location: current-state context, milestone/task scope, acceptance criteria, validation, risk, stop condition, or the source appendix with cross-references from affected files.

## Decomposition

Use deliverable-first decomposition:

1. Identify outcomes and deliverables before tasks.
2. Check that all in-scope goals map to deliverables.
3. Check that every deliverable maps back to an in-scope goal.
4. Split deliverables into milestones.
5. Split milestones into executable task files.

For user-facing products, preserve the user journey. Avoid plans that fully build one technical layer while leaving no usable end-to-end path.

For contract-heavy work, place known contracts directly in the task files that
will implement them. Relevant contracts include expected files/modules,
interfaces, API request/response shapes, data models, state transitions,
permissions or roles, migration rules, workflow protocols, fixture expectations,
and behavioral tests. When a required contract is unknown, create discovery or
decision work and name which later tasks depend on the result.

## Sequencing

Order work by:

- Hard dependencies.
- Risk reduction.
- Need for architectural or library decisions.
- Need for baseline tests or validation tooling.
- Thin end-to-end delivery path.
- User value.
- Release and handoff readiness.

Good early tasks often include:

- Repository/current-state discovery.
- Test and build command verification.
- Architecture boundary or data model decision.
- Minimal vertical slice.
- High-risk integration spike.

Defer polish, optional enhancements, broad content expansion, and low-risk variants until core flows and validation are stable.

## Milestones

Each milestone should include:

- Stable milestone ID such as `M01`.
- Objective and user/system outcome.
- Included task IDs.
- Entry criteria.
- Exit criteria.
- Deliverables.
- Validation gates.
- Risks and decision points.

Avoid milestones that are only calendar phases. A milestone should create a usable or clearly enabling increment.

## Task Sizing

Each task file should represent one coherent implementation outcome. Split a task when:

- It has multiple unrelated deliverables.
- It needs unrelated validation paths.
- It mixes discovery, implementation, and release work without a reason.
- It crosses too many ownership or module boundaries.
- It cannot be completed by one implementation agent in a bounded work session.

Create an earlier discovery or decision task when implementation depends on unresolved architecture, library selection, external access, unclear current state, or a core contract that would otherwise need to be invented while coding.

## Validation

Plan validation at three levels:

- Task validation: tests/checks for a single task.
- Milestone validation: acceptance checks before moving to the next milestone.
- Final validation: release, handoff, documentation, security/privacy, and regression checks.

When commands are unknown, write discovery steps instead of inventing commands.
