# Home Assistant setup and policy workflow

## Local development status

The `wolf_cwl2` component can currently be loaded from this repository's
`custom_components` directory in the locked test host. HACS/manual release is
not yet installable from an external repository because approved URLs, code
owner, license, brand asset, and an exact published client requirement are
still external blockers.

## Add one appliance

Start the WOLF CWL-2 integration from Home Assistant's integrations UI and
enter:

- gateway host and port;
- downstream Modbus device ID;
- `modbus_tcp` or `rtu_over_tcp`; and
- address offset 0 for normal addressing or -1 for one-based gateway mapping.

Setup opens a read-only client, reads the serial number and appliance type, and
closes it. It does not poll all datapoints, restore desired values, create
background work, or write the appliance. The verified 12-digit serial becomes
the stable entry/device identity. Configure each additional appliance as a
separate entry; duplicate serials are rejected even if reached through another
gateway endpoint.

## Change an endpoint

Use the entry's reconfigure action after moving or replacing a gateway. Home
Assistant accepts the new connection facts only if the live serial matches the
existing entry. A different serial aborts without changing the entry. Create a
new entry for a genuinely different appliance.

## Runtime policy

The options form selects one authority mode:

- `monitor_only` for read-only monitoring;
- `temporary` for safe live controls without desired ownership; or
- `persistent` for durable desired ownership, reconciliation, profile
  application, and profile capture.

Defaults are 5 seconds fast, 60 seconds slow, 300 seconds static, and 30 seconds
reconciliation. Every interval must be at least 5 seconds; invalid values are
rejected rather than changed silently. Holding-register and optional-extension
tiers can be disabled independently. Saving valid options performs one targeted
entry reload.

**Allow guarded appliance reset** is disabled by default. Enabling it does not
create a reset entity or bypass the remaining authority, administrator,
confirmation, target, and live-identity checks. See the
[guarded reset workflow](home-assistant-reset-actions.md).

For privacy-safe diagnostic downloads, persistent recovery issues, reload, and
removal guidance, see
[Home Assistant diagnostics and recovery](home-assistant-diagnostics-and-recovery.md).

The first successful refresh registers all 83 reviewed sensor dispositions.
The 23 curated read entities load immediately; advanced and diagnostic sensors
remain visible but disabled in the entity registry until explicitly enabled.
States are cache-only; disconnection, stale tier data, or an unavailable
register makes only the affected surface unavailable. Stable unique IDs combine
the verified serial and canonical client key, so endpoint and title changes
preserve Recorder history. Complete control and profile behavior is added by
the remaining active plan tasks.

Safe numeric, enum, and Boolean settings appear as native number, select, and
switch entities. In monitor-only mode these controls deliberately remain
visible but reject service calls. Temporary mode writes and verifies only the
live appliance. Persistent mode first stores desired ownership, then writes and
verifies the appliance; if the live step fails, the desired value remains
queued for the reconciliation workflow.

Persistent reconciliation uses the configured reconciliation interval and the
same coordinator/lock as polling. Switching away from persistent mode leaves
desired values stored but dormant. Switching back does not write them. Use
**Resume desired ownership** to explicitly force and resume them, or **Clear
desired ownership** to release them without changing the appliance's current
values.
