# Implementation Roadmap

## Roadmap Summary

The roadmap reduces immutable and release risk first, makes the reusable client
safe for a Home Assistant host, then delivers a thin multi-device monitoring
slice before expanding entity breadth and mutation features. Profiles and
resets arrive only after authority, persistence, concurrency, and availability
are proven. Operations and release gates close the work.

## Full Ordered Sequence

1. **TASK-001 — Resolve product and release contract gates.** Confirm immutable
   identifiers, supported scope, compatibility/release ownership, mode edge
   behavior, date/time UX, polling/freshness policy, identity evidence, retry
   policy, and entity-review rules.
2. **TASK-002 — Establish architecture records and HA test baseline.** Record
   ownership boundaries and prove the repository can execute the selected HA
   test/validation environment without changing product behavior.
3. **TASK-003 — Extract repository-backed desired/profile contracts.** Add
   async host-neutral persistence protocols and store-independent profile
   resolution/capture while preserving file behavior.
4. **TASK-004 — Add direct runtime construction and lifecycle controls.** Build
   the public non-file configuration path, initial-poll suppression, disabled
   state output, and explicit background/restore behavior.
5. **TASK-005 — Make setting validation context-aware.** Validate relational
   changes against fresh confirmed peers and define public compound-operation
   semantics.
6. **TASK-006 — Make the client host-safe and lightweight.** Move file work off
   loop, sanitize logs/errors, extract reusable profile defaults, and make
   Textual optional.
7. **TASK-007 — Qualify and release the client package.** Build/install the
   wheel, validate PyModbus/Home Assistant compatibility, and publish the exact
   dependency version when external authority exists.
8. **TASK-008 — Scaffold the custom component and HA harness.** Add the
   component/HACS Markdown-planned deliverables through test-first
   implementation: manifest, translations, config-entry skeleton, and Core-
   shaped tests.
9. **TASK-009 — Implement config, reconfigure, and options flows.** Probe
   identity without writes, prevent duplicate serials, support multi-entry
   endpoints, and validate authority/polling choices.
10. **TASK-010 — Implement the versioned per-entry HA Store.** Adapt the public
    desired/profile protocols to one transaction owner with migrations and
    removal isolation.
11. **TASK-011 — Deliver the multi-entry monitoring vertical slice.** Add one
    coordinator/scheduler/lock/runtime per entry, exactly one first poll,
    verified identity, tier freshness, setup retry, reload/unload, and a minimal
    read surface.
12. **TASK-012 — Classify every catalogue key.** Approve and validate the
    complete HA-only semantic overlay, curated defaults, composites, and action
    exclusions.
13. **TASK-013 — Implement read entities and Recorder semantics.** Deliver all
    sensor/binary/diagnostic read surfaces with stable IDs, legal units/classes,
    local optional failures, and no volatile attributes.
14. **TASK-014 — Implement authority modes and safe control entities.** Add
    number/select/switch mutations, confirmed write publication, mode guards,
    typed error translation, and cross-setting preflight.
15. **TASK-015 — Implement persistent reconciliation and mode transitions.** Add
    verified startup/reconnect restore, due reconciliation, dormant ownership,
    explicit resume/clear flows, retry observability, and ownership release.
16. **TASK-016 — Implement profile application and selection.** Add dynamic
    profile options, serialized temporary/persistent apply, partial failure,
    lineage separation, and last-successful-application state.
17. **TASK-017 — Implement TUI-equivalent profile capture.** Add preview/save,
    revisions, overwrite graph validation, option refresh, and exact desired-
    delta semantics in the allowed mode.
18. **TASK-018 — Implement guarded reset actions.** Add filter and appliance
    reset server-side gates, permissions, serial verification, dispatch-only
    success, invalidation, and reconnect behavior.
19. **TASK-019 — Complete diagnostics, repairs, migrations, and privacy.** Add
    redacted operational evidence, actionable repairs only, schema behavior,
    migration tests, and leak/cancellation hardening.
20. **TASK-020 — Complete documentation and release validation.** Finalize user
    workflows, HACS/manual packaging, exact dependency checks, disposable
    install tests, read-only physical validation, release evidence, and move the
    completed plan when all gates pass.

## Sequencing Rationale

- TASK-001 prevents immutable domain/identity/release facts from being encoded
  provisionally in component files.
- TASK-002 establishes test and documentation ownership before behavioral
  changes, satisfying repository TDD and system-of-record requirements.
- TASK-003 through TASK-006 remove filesystem, event-loop, lifecycle, and
  dependency blockers before Home Assistant code depends on new public APIs.
- TASK-008 through TASK-011 form the earliest usable end-to-end slice: two
  isolated config entries can configure, poll, become unavailable, recover, and
  unload safely.
- The complete read surface precedes controls so identity, cadence,
  availability, and Recorder contracts are stable before mutation is added.
- Authority and persistent ownership precede profiles because profile apply and
  capture reuse those semantics.
- Reset actions arrive last among mutations because they intentionally disrupt
  connectivity and have the strongest safety gates.
- Release hardening waits for complete behavior but the published client is
  qualified early because an exact installable requirement is a packaging hard
  dependency.

## Thin End-To-End Path

The first vertical slice ends at TASK-011:

- a user can manually add two distinct appliances;
- stable serial-backed device identities are created;
- one coordinator per entry polls fast/slow/static tiers;
- a minimal read-only value becomes visible and unavailable/recoverable;
- disabling every entity does not stop the entry-owned scheduler;
- options/reconfigure reload only the targeted entry; and
- unload/remove leak no transport, task, or foreign entry state.

This slice intentionally excludes broad entity metadata, writes, profiles, and
resets, allowing lifecycle errors to be fixed before surface expansion.

## Parallelization Opportunities

- After TASK-002, release-metadata gathering from TASK-001 can continue while
  the client test design is refined, but implementation must not encode pending
  immutable values.
- After TASK-006, TASK-007 package qualification and TASK-008 component/test
  scaffolding can overlap; the final manifest pin waits for TASK-007.
- After TASK-011, reviewed semantic-overlay work in TASK-012 can be partitioned
  by operator domain, but one owner must validate exactly-once coverage and
  reconcile cross-platform decisions.
- Documentation drafts may accompany each task, but TASK-020 owns final user
  and release validation rather than backfilling architecture facts.
- Do not parallelize mutations against the same files/runtime contract without
  explicit file ownership; the client persistence seam, HA Store, runtime lock,
  and profile engine are high-conflict areas.

## Replanning Checkpoints

- After TASK-001 if the domain, model scope, distribution, or package boundary
  changes.
- After TASK-005 if safe relational validation requires a materially different
  snapshot/transaction API.
- After TASK-007 if the client cannot be published or PyModbus conflicts with
  the selected Home Assistant environment.
- After TASK-011 if the one-coordinator design cannot remain live without
  listeners or if serial identity is unsuitable.
- After TASK-012 if complete entity coverage requires new platforms or
  composites not represented in this plan.
- After TASK-015 if persistent reconciliation needs a new retry/suspension state
  machine.
- Before TASK-020 if HACS or Home Assistant requirements have changed since the
  2026-08-11 research snapshot.
