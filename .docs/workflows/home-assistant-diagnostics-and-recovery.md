# Home Assistant diagnostics and recovery

## Download safe diagnostics

Use Home Assistant's integration or device diagnostics download for a loaded
WOLF CWL-2 entry. Both surfaces return the same summary: integration/client
versions, authority and polling policy, connection/coordinator health,
connection generation, tier success/freshness, and availability/error counts
with canonical register keys.

The download excludes gateway host/port/unit ID, serial and config-entry
identity, profile names/descriptions/settings, desired and live values, raw
words, timestamps, and exception text. Never attach Home Assistant's private
Store files or raw debug logs as a substitute for this diagnostic download.

## Respond to a repair

The integration creates persistent repairs only when operator action can help:

- **Appliance identity changed:** reconfigure the entry to the correct gateway
  endpoint, or remove and add the appliance again.
- **Stored data is invalid:** restore Home Assistant from a known-good backup,
  or remove and add the affected entry if losing its HA-owned desired state and
  profiles is acceptable.
- **Stored data is newer:** install the integration version that created the
  data. Do not hand-edit the private Store document.

Repair identifiers use an opaque entry hash and contain no endpoint or device
identity. Dismissing a repair does not bypass its setup gate. A successful Store
load or live serial verification removes the corresponding repair.

Ordinary gateway disconnection is not a repair. Home Assistant keeps the entry
in retry/unavailable state and the existing coordinator reconnect path handles
recovery.

## Reload, unload, and remove

Reload applies connection/options changes only to the selected entry. Unload
first rejects new mutations, drains any operation holding the entry lock,
removes scheduler/listener ownership, and closes transport. Another appliance
continues independently if one entry is blocked.

Removing an entry deletes only its private `wolf_cwl2.<entry_id>` Store
document. This permanently removes that entry's HA-owned desired state,
lineage, selector marker, and profiles; it does not reset or otherwise write the
appliance.
