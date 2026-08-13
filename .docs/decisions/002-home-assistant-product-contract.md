# Decision 002: Home Assistant product and safety contract

## Status

Accepted for local implementation on 2026-08-11. MIT licensing, Julian Kimmig
authorship/code ownership, and the public `JulianKimmig/wolf-325` repository
were accepted on 2026-08-13. Remaining publication authority and fleet-wide
identity evidence remain explicitly blocked as described below.

## Context

The native integration needs stable identifiers, a tested host baseline, clear
authority boundaries, and safe defaults before it can create config entries or
entities. The user selected a manual/HACS-first integration, multiple devices,
second-based polling, Home Assistant-owned profiles, three authority modes,
exact TUI profile capture, a complete curated entity surface, and guarded—not
ordinary—dangerous operations.

## Decision

- The immutable integration domain is `wolf_cwl2`. The first release supports
  WOLF CWL-2-325 appliances using the generation-1 register catalogue in this
  repository. Other variants require separate read-only catalogue evidence.
- Home Assistant 2026.2.3 on Python 3.13.2 or newer within the Python 3.13 line
  is the locally tested minimum. The host harness is pinned to
  `pytest-homeassistant-custom-component==0.13.316`. The standalone client
  continues to support Python 3.11 and newer.
- Config entries use the verified 12-digit appliance serial as their unique ID.
  Endpoint values never substitute for identity. One-device evidence cannot
  prove fleet-wide uniqueness, so multi-firmware read-only validation remains
  a release evidence item.
- Authority is one of `monitor_only`, `temporary`, or `persistent`. Temporary
  mode cannot capture dormant desired state. Persistent mode is required for
  TUI-equivalent profile capture.
- Default intervals are 5 seconds for fast values, 60 seconds for slow values,
  300 seconds for static values, and 30 seconds for reconciliation. Every
  configured interval has a hard 5-second floor and invalid input is rejected,
  never clamped. A tier is stale after two missed configured intervals.
- The four device date/time settings have no writable entity in the first
  release. Read-only values may be classified normally; a future composite
  write action requires a separate all-fields failure contract.
- Reconciliation reports categorized failures and uses coordinator cadence. It
  does not silently suspend desired ownership at an invented failure count.
- Counters receive no total/total-increasing state class without physical
  semantic evidence. The complete entity overlay owns default-enabled review.
- Communication settings have no writable entities. Filter reset and appliance
  reset may only be guarded actions; appliance reset must be opt-in and require
  an exact server-validated confirmation value. No raw register action exists.

## External release blockers

The project uses the MIT license with `Copyright (c) 2026 Julian Kimmig`, and
package metadata names Julian Kimmig as author. The public repository is
`https://github.com/JulianKimmig/wolf-325`; its README and issue tracker are the
approved documentation/support targets, and `@JulianKimmig` is the approved
code owner. Production publication targets PyPI project `wolf-325`, owned by
Julian Kimmig. The sanitized source was published as a new parentless `main`
root; the archival development history remains local. The matching PyPI Trusted
Publisher and exact release/tag actions remain unresolved. Those facts are not
guessed. They block publishing the client, final manifest requirements, HACS
publication, and TASK-020 release completion, but do not block local
integration behavior.

<!-- TODO(user): Configure the matching PyPI Trusted Publisher and authorize
the release tag before TASK-007 or TASK-020 can be completed. -->

## Consequences

- Config-entry, device, and entity identities survive endpoint changes.
- The integration can be developed and tested without claiming a releasable
  artifact or exposing dangerous register writes.
- Supporting a newer Home Assistant/Python line requires an additional locked
  test environment; lowering the minimum requires equivalent evidence.
- Physical validation remains read-only unless the user separately authorizes
  device writes or resets.
