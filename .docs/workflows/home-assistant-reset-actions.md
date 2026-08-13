# Home Assistant guarded reset workflow

## Scope and safety

Filter-warning and appliance reset are one-shot actions, not settings. They do
not appear as entities, never become persistent desired state, and cannot be
stored in profiles. The integration exposes no generic Modbus write action.
Automations can carry service context, so confirmation phrases are accident
guards rather than proof that a person is physically present.

No physical reset is part of automated validation. A live appliance reset must
be separately and explicitly authorized by the operator.

## Reset a filter warning

Run **WOLF CWL-2: Reset filter warning** against exactly one loaded device entry
and enter `EXECUTE ACTION` exactly. The entry must use temporary or persistent
authority. Under the entry operation lock, the integration rechecks that unload
has not started, refreshes the live serial, requires it to match the entry, and
then calls the public client reset operation. The response reports the public
client's verified result.

## Reset an appliance

First enable **Allow guarded appliance reset** in that entry's options. Run
**WOLF CWL-2: Reset appliance** from a Home Assistant administrator context,
target exactly one loaded entry, and enter `RESET APPLIANCE` exactly. Temporary
or persistent authority and a fresh matching serial are also mandatory.

Success means only that the command was sent. It does not claim that the
appliance rebooted or recovered. The integration closes the stale connection,
marks coordinator data unavailable, makes every polling tier immediately due,
and lets ordinary coordinator polling reconnect and verify the serial.

## Failure behavior

Missing/unloaded targets, monitor mode, wrong phrases, disabled appliance opt-in,
non-administrator appliance calls, stopping entries, changed identity, and
communication failures all reject without a reset write or Store mutation.
Errors are translated and do not expose endpoint or raw transport details.
