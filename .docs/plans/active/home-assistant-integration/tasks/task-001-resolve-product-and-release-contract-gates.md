# TASK-001: Resolve Product And Release Contract Gates

## Status

- Status: done; external release facts explicitly blocked
- Milestone: M01
- Dependencies: none
- Blocks: TASK-002–020 where the recorded decisions apply

## Expected Current State

The repository has no Home Assistant domain, public-release metadata, minimum
HA version, or approved policy for several safety/UI edges. The thought
synthesis and active plan list the unresolved decisions without encoding them.

## Source Details This Task Must Preserve

- Manual/HACS first with a future Core-compatible architecture.
- Multiple devices, second-based polling, three authority modes, HA-owned
  profiles, complete-but-curated entities, exact TUI capture semantics, and
  guarded dangerous actions.
- Missing facts must remain explicit blockers rather than guessed defaults.

## Implementation Contracts And Gaps

Record durable decisions for:

- immutable integration domain and supported model/appliance-type scope;
- license, public repository, docs/issue URLs, GitHub code owner, package-index
  owner/name, integration/client version strategy;
- minimum Home Assistant and supported Python versions;
- temporary-mode capture permission;
- composite UX and failure contract for four non-restorable date/time fields;
- measured poll minimum and freshness multiplier;
- serial uniqueness/stability and compatible identity values;
- persistent mismatch retry/backoff/suspension/repair thresholds;
- default-enabled entity review and counter statistic evidence; and
- whether guarded appliance reset is in the first release.

Use stable decision IDs from `03-dependencies.md`. Do not create implementation
files in this task.

## Implementation Plan

1. Re-read the source appendix, thought synthesis, current catalogue identity /
   date-time definitions, package metadata, and official research notes.
2. Collect answers/evidence from the user for external ownership and safety
   decisions.
3. Where physical evidence is required, define a read-only validation protocol;
   do not perform writes.
4. Record each decision, rationale, rejected alternatives, compatibility impact,
   and revisit trigger in `.docs/decisions/` or the owning contract/workflow.
5. Update `decision-log.md`, the dependency gates, assumptions, and affected
   task files without renumbering tasks.
6. Mark unresolved external release facts as blockers for TASK-007/TASK-020,
   while allowing safe local work whose contracts are settled.

## Expected Deliverables

- Approved or explicitly blocked DEC-001 through DEC-009.
- Durable system-of-record decision entries and cross-links.
- Exact dependent-task readiness updates.

## Acceptance Criteria

- No immutable identifier, release owner, compatibility promise, threshold, or
  safety behavior remains an implicit assumption at its implementation gate.
- User choices and their rationale are traceable to task IDs.
- Physical evidence requests remain read-only unless separately authorized.

## Validation

- Review all open TODOs in the plan and thought summary; each maps to a decision
  or explicit blocker.
- Run Markdown link/check tooling if already available; do not invent a new
  command without recording it.
- `git diff --check` and peer/user review of decision wording.

## Edge Cases And Risks

- A requested domain may conflict with an existing Home Assistant domain.
- Package/public repository authority may be unavailable even when local
  development is possible.
- One physical device cannot prove fleet-wide serial uniqueness; record the
  evidence limit.

## Completion Evidence

Decision 002 records the accepted local domain, model scope, tested host,
identity, polling, authority, date/time, counter, reconciliation, and reset
contracts. MIT licensing, Julian Kimmig authorship/code ownership, and the
public repository/docs/issues URLs were resolved on 2026-08-13. Package-index
target/ownership was then resolved as PyPI `wolf-325`, owned by Julian Kimmig.
The sanitized source was published as a parentless public `main` root while the
archival `HA` history remained local. Exact trusted-publisher/release authority
and broader fleet identity evidence remain named external blockers for
TASK-007/TASK-020. Physical writes were not performed. Commit hash is recorded
after this closed slice.

## Stop Conditions

- The user cannot authorize immutable/release choices required by a dependent
  task.
- Serial identity is unstable/absent or model scope cannot be safely defined.
- The requested choice materially changes the native-integration architecture;
  replan before implementation.
