# Home Assistant profile workflow

## Ownership and selection

Each config entry owns an independent profile catalogue in its private Home
Assistant Store. Five canonical examples seed a new Store once. The integration
does not watch, import, or overwrite CLI/TUI profile files.

The device's **Profile** select lists the current Store catalogue. Its state is
the last profile fully applied by Home Assistant in the current authority
contract. It does not claim that live values still match the profile. External
writes or local-panel changes therefore do not change the selector state.

## Applying a profile

- Monitor-only mode rejects before Store or Modbus mutation.
- Temporary mode resolves the profile through the public client engine and
  writes its settings without desired ownership or lineage. Successful selector
  state is runtime-only and clears on reload.
- Persistent mode atomically commits resolved desired state and `last_profile`
  lineage before sequential verified writes. It advances the durable
  `last_applied_profile` marker only after every write succeeds.

Apply order, `extends`, `replace`, `unset`, value normalization, relational
preflight, and verification are the public client contracts. Partial success is
not rolled back. In persistent mode, intended desired values remain queued for
reconciliation and the selector does not advance.

## Profile capture

Use the **Preview profile capture** action with a device entry to inspect the
exact delta, base, `unset`, `replace`, change flag, and Store revision. Use
**Save profile** with a suffix-free name, optional description, explicit
overwrite flag, and optionally that expected revision. Capture requires
persistent mode and uses durable desired state plus exact `last_profile`
lineage—never live telemetry or temporary writes.

Collision, invalid/empty delta, stale revision, or an invalid prospective
inheritance graph fails without mutation. Success performs zero Modbus I/O,
refreshes selector options without a reload, and does not apply/select the new
profile or alter desired/lineage.
