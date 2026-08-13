# TASK-004: Add Direct Runtime Construction And Lifecycle Controls

## Status

- Status: done
- Milestone: M02
- Dependencies: TASK-003
- Blocks: TASK-005–006, TASK-009, TASK-011

## Expected Current State

`WolfCWL2` requires a JSON config path. `start()` performs an all-tier poll and
may restore/start background tasks. HA needs explicit construction and exactly
one coordinator-owned initial refresh.

## Source Details This Task Must Preserve

- `WolfCWL2(config_path=...)` remains stable for CLI/TUI.
- HA disables state-file output and controller-owned background/reconcile tasks.
- No persistent restore occurs before live serial verification.

## Implementation Contracts And Gaps

- Public normalized runtime configuration model/factory accepts connection,
  timeout/retry, poll/verification, repository, and state-output choices.
- Lifecycle supports no-initial-poll, `restore=False`, `background=False`, and
  read-only mode explicitly.
- `start()`/`stop()` remain idempotent and cleanup-safe.
- Snapshot generation works after initialization and before/after coordinator
  polling as documented.

## Implementation Plan

1. Write failing tests for direct construction, no hidden config file, no
   initial request, no background task, disabled state output, and cleanup.
2. Add a normalized typed runtime configuration boundary and factory/classmethod
   while retaining the config-path constructor.
3. Add backwards-compatible initial-poll control or an equivalent explicit
   initializer; existing callers keep their current default behavior.
4. Inject repositories from TASK-003 and make read-only/background/restore
   choices explicit.
5. Test setup failure and stop after partial initialization.
6. Update public exports and lifecycle/config contracts.

## Expected Deliverables

- Public direct-runtime construction API.
- Exactly controllable initial poll/background/restore/state output.
- Backward-compatible file constructor.

## Acceptance Criteria

- HA-style initialization causes zero Modbus requests until explicit poll.
- Existing CLI/TUI startup behavior remains unchanged.
- No background/reconcile task exists when disabled.
- Stop closes partially and fully initialized clients without leaks.

## Validation

- Runtime edge/controller/transport tests plus new construction tests.
- Fake-client request counts prove exactly zero/one initial poll cases.
- Full regression, line-count/docstring checks, `git diff --check`.

## Edge Cases And Risks

- Start currently catches initial communication failure; suppressing the poll
  changes where setup retry is owned.
- Direct config must reuse canonical validation rather than bypass defaults.
- Repository initialization errors must not open a transport.

## Completion Evidence

Implemented `RuntimeConfigStore`, `WolfCWL2.from_config(...)`, injected
repositories, `start(initial_poll=False)`, and disabled host-owned paths.
Behavior tests prove zero hidden first-poll requests and preserve legacy
defaults; commit hash is recorded after the closed slice is committed.

## Stop Conditions

- Exact no-double-poll behavior cannot be achieved compatibly.
- Direct config requires importing HA types into the client library.
- Cleanup cannot be proven under partial initialization.
