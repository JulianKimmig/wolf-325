# TASK-006: Make The Client Host-Safe And Lightweight

## Status

- Status: done
- Milestone: M02
- Dependencies: TASK-003–005
- Blocks: TASK-007–008

## Expected Current State

Client semantics are host-neutral, but file adapters can block the event loop,
connection logs/errors expose endpoint details, example profiles live in a
CLI-owned module, and Textual is mandatory.

## Source Details This Task Must Preserve

- CLI/TUI/file behavior and durable atomic writes.
- Base client contains transport/controller/profile logic only.
- HA diagnostics and logs must not expose endpoint, serial, or profile data.

## Implementation Contracts And Gaps

- File adapters offload filesystem traversal, JSON serialization, flush/fsync,
  and atomic replacement appropriately.
- Public errors and logs use categorized/sanitized context without raw endpoints.
- Reusable example profiles move to a host-neutral public location.
- Textual becomes an optional TUI extra; CLI/TUI entry points fail explicitly
  when their declared dependency is absent rather than adding a fallback.

## Implementation Plan

1. Add blocking-I/O detection tests for file adapters and sentinel-redaction
   tests for logs/public errors.
2. Refactor durable file operations to worker execution while preserving atomic
   replacement and exception behavior.
3. Sanitize transport connection/retry/error logging and exception formatting.
4. Extract example profile data from the CLI module without changing generated
   examples.
5. Move Textual to a TUI optional dependency and align development/test groups.
6. Add clean base-import tests proving `wolf_325` does not import/require
   Textual; test TUI installation separately.
7. Update packaging, architecture, and operational logging contracts.

## Expected Deliverables

- Nonblocking file-backed repositories.
- Redaction-safe client logs/errors.
- Reusable profile defaults.
- Lightweight base dependency set and explicit TUI extra.

## Acceptance Criteria

- Durable file semantics and existing examples remain identical.
- Sentinel endpoint/serial/profile strings never appear in client logs/errors.
- Base wheel import and controller construction work without Textual.
- Installed TUI extra preserves current TUI behavior.

## Validation

- Blocking/event-loop, config/profile, logging, package import, CLI/TUI, and full
  regression tests.
- Build metadata inspection and clean environment base/TUI imports.
- LOC/docstring checks and `git diff --check`.

## Edge Cases And Risks

- Offloading must not share mutable data unsafely across threads.
- Sanitized errors must retain actionable typed categories.
- Packaging extras can break existing `uv run wolf-cwl2-tui` developer flow if
  dev groups are incomplete.

## Completion Evidence

Implemented explicitly owned worker execution for filesystem operations,
sanitized connection logs/errors, reusable example profiles, and a base package
with Textual only in the `tui` extra. Focused redaction/metadata tests and the
full suite pass; commit hash is recorded after the closed slice is committed.

## Stop Conditions

- Atomic file durability cannot be preserved off-loop.
- PyModbus/client import still pulls Textual transitively.
- Sanitization removes error categories required by callers.
