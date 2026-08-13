# Home Assistant Integration Implementation Plan

## Plan Identity

- **Plan:** Native Home Assistant integration for WOLF CWL-2 control
- **Slug:** `home-assistant-integration`
- **Priority:** 9
- **Status:** active; local implementation and qualification complete, external
  publication and a fresh reachable-device gate blocked
- **Created:** 2026-08-11
- **Repository plan root:** `.docs/plans/active/` per the local system-of-record
  rule, overriding the planning skill's generic `.plan/` default
- **Integration domain:** `wolf_cwl2`

## Source Request Summary

Build a native Home Assistant custom integration that exposes individual WOLF
CWL-2 datapoints and safe controls, refreshes values automatically for Recorder
history and graphs, applies profiles as multi-setting changes, and saves new
profiles with the same persistent desired-state capture semantics as the TUI.

The user selected:

- manual/HACS distribution first, with a future Core-compatible architecture;
- multiple devices from release one;
- configurable polling intervals in seconds;
- per-entry `monitor_only`, `temporary`, and `persistent` authority modes;
- Home Assistant-owned profile storage;
- all supported datapoints classified, with curated defaults; and
- no ordinary entities for dangerous communication settings or appliance reset.

## Source Detail Location

Read [appendix-source-requirements.md](appendix-source-requirements.md) for the
non-lossy product, lifecycle, storage, safety, entity, profile, and validation
contracts. Read [research-notes.md](research-notes.md) for current official Home
Assistant and HACS facts used by the plan.

## How To Use This Plan

1. Read this file, [00-current-state.md](00-current-state.md), and
   [appendix-source-requirements.md](appendix-source-requirements.md).
2. Follow task dependencies in [03-dependencies.md](03-dependencies.md); do not
   skip a decision or validation gate because later code appears independent.
3. Open exactly one ready task from `tasks/` and follow its TDD sequence.
4. Update the task status, evidence, roadmap, milestones, and handoff after each
   closed implementation outcome.
5. Update the owning `.docs` architecture/contract/domain/workflow record in the
   same commit as the behavior it describes.
6. Keep all Python source files below 300 lines and end each closed slice in an
   atomic commit. Never push.

## File Map

- [00-current-state.md](00-current-state.md) — starting system and preserved
  requirements.
- [01-implementation-roadmap.md](01-implementation-roadmap.md) — ordered
  start-to-finish sequence.
- [02-milestones.md](02-milestones.md) — milestone outcomes and gates.
- [03-dependencies.md](03-dependencies.md) — task graph, critical path, external
  dependencies, and decision gates.
- [04-validation-and-risk.md](04-validation-and-risk.md) — TDD, acceptance,
  privacy, physical safety, and risk register.
- [05-agent-handoff.md](05-agent-handoff.md) — execution and replanning rules.
- [appendix-source-requirements.md](appendix-source-requirements.md) — non-lossy
  source-retention ledger.
- [decision-log.md](decision-log.md) — accepted, provisional, and deferred
  design decisions.
- [research-notes.md](research-notes.md) — official external sources.
- `tasks/` — twenty executable implementation task files.

## First Recommended Task

[TASK-001: Resolve product and release contract gates](tasks/task-001-resolve-product-and-release-contract-gates.md)
is ready. It prevents immutable identifiers, compatibility promises, release
metadata, date/time UX, and safety thresholds from being invented during code
implementation.

## Current Status

- Perspective analysis: complete.
- User clarification: complete.
- Four-agent reasoning and adversarial synthesis: complete.
- Official Home Assistant/HACS research: complete as of 2026-08-11.
- Plan validation: passed on 2026-08-11; 6 milestones, 20 executable tasks,
  Markdown-only scope, complete task-section coverage, and clean whitespace.
- Product implementation: TASK-001 through TASK-019 complete except for the
  external TASK-007 publication step. TASK-020 local documentation, HACS shape,
  artifact qualification, and release handoff are complete. Publication,
  public-validator/disposable-install gates, and a fresh reachable-device audit
  remain blocked, so this plan correctly stays active.
