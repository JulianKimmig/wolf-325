# TASK-002: Establish Architecture And Home Assistant Test Baseline

## Status

- Status: done
- Milestone: M01
- Dependencies: TASK-001
- Blocks: TASK-003, TASK-008

## Expected Current State

Product/release decisions required for development are recorded. Existing tests
cover the client/CLI/TUI, but no HA test dependency, Core-shaped test tree, or
HA system-of-record boundary exists.

## Source Details This Task Must Preserve

- TDD precedes every code change.
- Use `uv`, pytest, real source logic, and external-boundary fakes only.
- One client/public facade, one HA owner per entry, HA-owned storage, stable
  identity, confirmed state, and sources below 300 lines.

## Implementation Contracts And Gaps

- Choose a HA test package/version matching DEC-002 minimum HA/Python support.
- Discover exact `uv` commands for focused HA tests, existing regression tests,
  formatting/lint/type checks, hassfest/HACS validation, and wheel checks.
- Define expected test layout under `tests/components/<domain>/`.
- Create/repair owning `.docs` records for the HA domain, contracts, decisions,
  and workflows before implementation facts appear.

## Implementation Plan

1. Run the existing test suite and record the clean baseline.
2. Inspect `pyproject.toml`, `uv.lock`, pytest configuration, CI files, and
   current test fixtures.
3. Add the selected HA test/dev dependencies through `uv` only after tests for
   the expected harness behavior are specified.
4. Establish a minimal HA test fixture that loads custom integrations and can
   use the existing external Modbus fake without mocking controller methods.
5. Add a baseline import/test proving unchanged `wolf_325` and the HA test host
   coexist.
6. Create/update `.docs/ARCHITECTURE.md`, `.docs/code-relationships.md`, and
   initial HA domain/contract/decision records with approved boundaries, not
   unimplemented completion claims.
7. Record exact commands in the appropriate workflow docs.

## Expected Deliverables

- Reproducible HA pytest environment managed by `uv`.
- Core-shaped test directory and external-boundary fixtures.
- Baseline validation command ledger.
- Accurate architecture/relationship/contract scaffolding.

## Acceptance Criteria

- Existing suite remains green.
- A minimal HA test runs without product implementation.
- No test replaces source controller/runtime/profile behavior with mocks.
- Documentation names ownership and dependency direction accurately.

## Validation

- Run existing full tests and the new minimal HA harness test.
- Verify dependency lock consistency and source module line limits.
- `git diff --check`; inspect that no runtime integration behavior was claimed
  complete.

## Edge Cases And Risks

- Selected HA test package may constrain Python versions.
- Existing PyModbus pin may conflict with Home Assistant's environment.
- Test fixtures can accidentally mock too high in the stack.

## Completion Evidence

The dev group pins `pytest-homeassistant-custom-component==0.13.316` and narrows
only development to Python 3.13.2–3.13.x; the client remains Python 3.11+.
Core-shaped tests prove Home Assistant 2026.2.3, its `hass` fixture, and the
public client coexist. The HA domain, config-entry/Store contract, decision,
and development workflow record one-way ownership and exact commands. Commit
hash is recorded after this closed slice.

## Stop Conditions

- No compatible HA/Python/test dependency combination exists.
- Adding the harness requires changing product behavior before its TDD task.
- Architecture decisions from TASK-001 remain unresolved.
