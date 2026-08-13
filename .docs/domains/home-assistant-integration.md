# Home Assistant integration domain

## Purpose

The `wolf_cwl2` custom integration presents one WOLF CWL-2-325 appliance per
Home Assistant config entry. It adapts the public `wolf_325` client; it does not
duplicate Modbus addresses, codecs, validation, profile resolution, or desired
state rules.

## Ownership boundaries

Each loaded config entry owns exactly one controller, one Home Assistant Store,
one profile repository, one whole-operation lock, and one polling coordinator.
Home Assistant owns all scheduling. The client starts with initial polling,
restore, background loops, and file state output disabled.

Entity properties are cache-only. Network reads, writes, reconciliation,
profile operations, and reset actions execute under the entry operation lock.
One entry failing or unloading must not mutate another entry's runtime, Store,
tasks, entities, or repair issues.

The HA semantic overlay classifies every canonical client key once: 83 sensor,
39 number, 20 select, 10 switch, and 2 guarded action dispositions. Thirty-six
curated ordinary entities are enabled by default; advanced and diagnostic
entities remain available for explicit registry enablement. See the
[entity contract](../contracts/home-assistant-entities.md).

## Authority modes

- `monitor_only` permits polling and read entities only.
- `temporary` permits safe writes without durable desired ownership.
- `persistent` persists desired ownership before device I/O and enables
  reconciliation, profile selection/application, ownership release, and exact
  desired-state profile capture.

All entity state represents confirmed device state. Queued desired state,
profile lineage, partial application, and errors are separate diagnostics and
must never be presented as a confirmed appliance value.

Safe number, select, and switch operations share the entry lock with polling.
The runtime rechecks authority, lifecycle, availability, connection, and serial
identity inside that lock, then delegates normalization, relational preflight,
persistence, write, and verification to the public client. Monitor mode rejects
before persistence or I/O; temporary mode never creates desired ownership;
persistent mode stores ownership before attempting the live write.

Persistent reconciliation is a coordinator deadline, not a second task. Before
each due operation it refreshes identity on a new connection and refreshes every
owned register, then applies only drifted values unless the connection
generation requires a forced restore. Failures remain queued and retry at the
configured interval; no unapproved failure-count suspension is invented.

Leaving persistent authority makes retained ownership dormant. Returning never
silently reasserts it: the operator must press Resume desired ownership or Clear
desired ownership. Resume authorizes durably before a forced apply; clear
removes desired keys without a Modbus write.

## Identity and polling

The appliance serial is the config-entry unique ID and the root of device and
entity identity. Host, port, unit ID, transport, and address offset are mutable
connection data. No endpoint fallback is allowed when serial verification
fails.

The coordinator batches due fast, slow, and static tiers. Defaults are 5, 60,
and 300 seconds; reconciliation defaults to 30 seconds. The hard interval floor
is 5 seconds. Disabled entities do not stop tier polling because reads are
block-oriented and the scheduler belongs to the entry, not to listeners.

The coordinator ticks at the shortest configured tier interval, compares
monotonic due deadlines, polls every due tier in one ordered call, and advances
each successful deadline from the current time. Missed intervals are skipped,
not replayed as bursts. A retained entry-lifetime listener keeps cadence active
when every entity is disabled. Tier freshness expires after two intervals.

Setup performs exactly one coordinator-owned all-tier poll and verifies the
serial before forwarding entities. A mismatch or connection failure stops the
client and enters Home Assistant setup retry. The controller owns no background
task or state-output file.

## Persistence and profiles

Home Assistant Store is authoritative for desired state, lineage, integration
policy, and profile documents for one entry. File-backed CLI/TUI profiles are
not watched or shared. The Store adapter implements the client repository
protocols and awaits durable persistence before exposing a successful mutation.

Profile capture is permitted only in persistent mode and uses the same desired
delta/`last_profile` lineage algorithm as the TUI. It never infers a profile
from live telemetry.

Profile application always uses the public client resolver and ordered write
path. Temporary application leaves Store desired/lineage untouched and records
success only for the current runtime. Persistent application saves desired and
lineage before I/O, then advances `last_applied_profile` only after every
read-back succeeds. Selector state is not a live-match claim.

## Safety exclusions

Communication configuration and date/time settings have no ordinary writable
entities in the first release. Reset registers are action-only and never enter
desired/profile state. Filter reset requires control authority, one loaded
target, an exact phrase, and a fresh serial match. Appliance reset adds an
explicit disabled-by-default option and administrator context, reports only
dispatch, invalidates cached availability, and reconnects through normal
coordinator polling. Raw Modbus access is out of scope.

## Diagnostics, repairs, and lifecycle

Both config-entry and device diagnostic downloads expose the same safe summary:
versions, policy, coordinator/connection health, tier success/freshness, and
categorized availability counts/keys. No endpoint, serial, entry identity,
profile content, desired/live value, raw word, timestamp, or exception text is
included.

Persistent repairs are limited to identity mismatch, invalid Store data, and
unsupported Store schema. Their stable IDs hash the config-entry identifier,
carry no sensitive data/placeholders, survive dismissal, and disappear only
after the relevant Store or live-identity check succeeds. Transient reachability
failure remains normal setup retry without a repair.

Unload marks the runtime stopping before platform teardown, drains the shared
operation lock, removes the retained scheduler, shuts down coordinator cadence,
and then closes transport. Per-entry locks/transports allow another appliance
to refresh even while one gateway request is blocked.

See [decision 002](../decisions/002-home-assistant-product-contract.md), the
[config-entry and Store contract](../contracts/home-assistant-config-entry-and-store.md),
the [reset workflow](../workflows/home-assistant-reset-actions.md), the
[diagnostics and recovery workflow](../workflows/home-assistant-diagnostics-and-recovery.md),
and the [development workflow](../workflows/home-assistant-development.md).
