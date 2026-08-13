# Dependencies And Decision Gates

## Task Dependency Table

| Task | Depends on | Blocks |
|---|---|---|
| TASK-001 | none | TASK-002–020 where decisions apply |
| TASK-002 | TASK-001 | TASK-003, TASK-008 |
| TASK-003 | TASK-001, TASK-002 | TASK-004–006, TASK-010, TASK-016–017 |
| TASK-004 | TASK-003 | TASK-005–006, TASK-009, TASK-011 |
| TASK-005 | TASK-003, TASK-004 | TASK-006, TASK-014 |
| TASK-006 | TASK-003–005 | TASK-007–008 |
| TASK-007 | TASK-006 | TASK-020 and final manifest pin |
| TASK-008 | TASK-001, TASK-002, TASK-006 | TASK-009–013 |
| TASK-009 | TASK-004, TASK-008 | TASK-011, TASK-019 |
| TASK-010 | TASK-003, TASK-008 | TASK-011, TASK-015–017, TASK-019 |
| TASK-011 | TASK-004, TASK-009, TASK-010 | TASK-012–019 |
| TASK-012 | TASK-008, TASK-011 | TASK-013–014 |
| TASK-013 | TASK-011, TASK-012 | TASK-014, TASK-019 |
| TASK-014 | TASK-005, TASK-011–013 | TASK-015–018 |
| TASK-015 | TASK-010–011, TASK-014 | TASK-016–017, TASK-019 |
| TASK-016 | TASK-003, TASK-010, TASK-014–015 | TASK-017, TASK-019 |
| TASK-017 | TASK-003, TASK-010, TASK-016 | TASK-019 |
| TASK-018 | TASK-011, TASK-014 | TASK-019 |
| TASK-019 | TASK-009–018 as applicable | TASK-020 |
| TASK-020 | TASK-007, TASK-019 | release/plan completion |

## Milestone Dependency Table

| Milestone | Depends on | Exit dependency |
|---|---|---|
| M01 | none | approved contracts and baseline |
| M02 | M01 | host-neutral client seams; artifact for release |
| M03 | M02 client seams; TASK-007 may continue in parallel | runnable monitoring slice |
| M04 | M03 | stable entity/Recorder contract |
| M05 | M04 | complete mutation/profile safety |
| M06 | M05 and published client from TASK-007 | installable release evidence |

## Critical Path

The behavioral critical path is:

`TASK-001 → TASK-002 → TASK-003 → TASK-004 → TASK-005 → TASK-006 → TASK-008 → TASK-009/TASK-010 → TASK-011 → TASK-012 → TASK-013 → TASK-014 → TASK-015 → TASK-016 → TASK-017 → TASK-019 → TASK-020`

TASK-007 is a parallel external-release path after TASK-006 but rejoins as a
hard dependency of TASK-020. TASK-018 can proceed after TASK-014/TASK-011 and
must complete before TASK-019.

## External Dependencies

- User decisions and evidence listed in TASK-001.
- A chosen supported Home Assistant release and compatible Python version.
- Home Assistant development/test packages discovered in TASK-002.
- Exact PyModbus compatibility with the selected Home Assistant environment.
- A matching PyPI Trusted Publisher for the selected Julian Kimmig-owned
  `wolf-325` project.
- Exact release-tag, package, and HACS publication authority.
- A local `brand/` asset for Home Assistant 2026.3+; an external Brands path is
  relevant only if an older supported host or later upstream target requires it.
- Access to the physical appliance and gateway for read-only validation.
- Separate explicit authority for any later physical writes or resets.

## Decision Gates

| ID | Decision | Required before | Default if assumable |
|---|---|---|---|
| DEC-001 | Immutable integration domain and model scope | component directory/manifest | working proposal `wolf_cwl2`; do not encode until approved |
| DEC-002 | Trusted Publisher and release authority | package/manifest publication | source push complete; remaining actions are external blockers |
| DEC-003 | Temporary-mode capture permission | TASK-017 | reject save in v1 |
| DEC-004 | Device date/time composite UX | TASK-012/013 | no writable exposure until approved |
| DEC-005 | Poll minimum and freshness multiplier | TASK-009/011 | minimum 5 seconds; measured final values required |
| DEC-006 | Serial identity stability/uniqueness | TASK-009/011 | no host fallback |
| DEC-007 | Persistent mismatch retry/suspension | TASK-015/019 | categorized backoff only; do not invent suspension |
| DEC-008 | Default entity set and counter classes | TASK-012/013 | TUI overview as candidate; no unproven totals |
| DEC-009 | Appliance reset included in v1 | TASK-018 | guarded action only if explicitly retained |

## Blocking Questions

The plan itself can proceed, but implementation must stop at the named gate
when the following remain unanswered:

1. What immutable domain and exact appliance/model scope should the first
   release promise?
2. Which Trusted Publisher, tag, and package/HACS publication actions are
   authorized?
3. May temporary mode save a profile from dormant historical desired state?
4. How should the four non-restorable device date/time fields appear and fail
   as one user operation?
5. What measured poll lower bound and freshness multiplier are safe?
6. Is the serial stable and unique across supported devices/firmware?
7. When should repeated persistent mismatch suspend retries and create a repair?
8. Which entities are initially enabled and which counters have verified total
   semantics?

TASK-001 owns these questions and records their dependent-task impact.
