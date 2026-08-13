# Decision 001: connected zero-word responses for optional definitions

## Status

Accepted on 2026-07-18.

## Context

The physical CWL-2-325 returns a successful Modbus function-4 response with a
byte count of zero for optional input register 4503
(`extension_hardware_version`). Repeated individual reads produce the same
frame. The TCP connection remains healthy, and adjacent extension definitions
4500 and 4504 return normal zero-valued payloads. The reference implementation
treated every short response as a communication failure, which aborted normal
static polling for the whole optional 4500..4505 block.

## Decision

When an optional block returns fewer words than requested while the connection
is still healthy, polling falls back to individual logical definitions. An
individual optional definition that repeatedly returns fewer words is marked
unavailable with a `short response` error. Required definitions and short
responses associated with a lost connection remain communication failures.

The physical audit classifies this connected, repeatable optional case as
`unsupported_optional`; it does not classify arbitrary timeouts or short
required responses that way.

## Consequences

- Supported values neighboring an absent extension value continue to update.
- `refresh` returns `None` for this unavailable optional definition and callers
  can inspect the precise state error.
- Required register integrity remains strict.
- Tests cover both optional block fallback and single-definition handling in
  [`test_transport_polling.py`](../../tests/test_transport_polling.py), with
  physical evidence from
  [`hardware/test_read_all.py`](../../tests/hardware/test_read_all.py).
