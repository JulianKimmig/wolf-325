# Home Assistant entity contract

## Classification ownership

[`entity_catalogue.py`](../../custom_components/wolf_cwl2/entity_catalogue.py)
is the Home Assistant-only semantic overlay. It classifies all 154 canonical
client keys exactly once while deriving addresses, codecs, ranges, enum values,
writability, safety flags, optionality, units, and poll tiers from
`wolf_325.REGISTERS`. It must never become a second wire schema.

The reviewed distribution is 83 sensors, 39 numbers, 20 selects, 10 switches,
and 2 guarded action-only values. Thirty-six ordinary entities are enabled for
new registry entries by default. Existing registry enablement is never changed
retroactively.

## Safety and writable surfaces

- Restorable safe numeric, enum, and Boolean settings map to number, select,
  and switch platforms respectively.
- The four appliance clock fields remain read-only sensors in version one.
- Modbus interface type, slave address, and serial speed remain disabled-by-
  default diagnostic sensors, never writable entities.
- Filter and appliance reset registers are guarded action-only dispositions.
- Unknown enum values remain readable sensor states. Select options come only
  from known canonical enum values.

All 69 safe setting dispositions register on native platforms: 39 numbers, 20
selects, and 10 switches. They remain visible in monitor-only mode so entity
domains and automations stay stable, but the shared mutation owner rejects a
request before Store or Modbus activity. Temporary mode passes `persist=False`;
persistent mode passes `persist=True`, which durably commits desired ownership
before device I/O. State remains the verified controller cache and is never
updated optimistically.

The mutation owner rechecks stopping state, authority, coordinator health,
connection, and serial identity after acquiring the per-entry operation lock.
Catalogue normalization, fresh relation-peer reads, cross-setting validation,
write ordering, and read-back verification remain client-owned. Caller mistakes
raise translated `ServiceValidationError`; communication and verification
failures raise translated `HomeAssistantError` without endpoint details.

## Recorder semantics

Instantaneous numeric telemetry may use the `measurement` state class when its
engineering meaning and unit are proven. Operating-time, filter-runtime, and
air-volume counters intentionally have no total or total-increasing state class
until physical behavior proves their reset and monotonicity contracts.

Entity state is confirmed cached device state. Raw words, poll timestamps,
errors, desired values, pending writes, and profile lineage never become
ordinary entity attributes. Availability combines global coordinator success,
live connection state, tier freshness, and the individual cached value.

All 83 sensor dispositions are registered. Curated sensors load immediately;
advanced and diagnostic sensors are registered disabled-by-integration and
therefore produce no Recorder state until an operator enables them. Enum
sensors deliberately remain plain string sensors so a firmware value such as
`unknown_99` stays observable instead of violating a closed HA enum option set.
Raw-word date data is rendered as a stable comma-separated scalar.

## Guarded action surface

Neither reset disposition creates an entity, desired value, profile setting,
or generic raw-register service. Both actions target exactly one loaded config
entry, reject monitor-only authority, acquire that entry's operation lock,
recheck lifecycle state, and refresh the live serial before dispatch.

Filter reset additionally requires the exact phrase `EXECUTE ACTION` and
returns only the public client's verified action status. Appliance reset
additionally requires the per-entry opt-in, the exact phrase
`RESET APPLIANCE`, and an administrator-backed Home Assistant service context.
Its response is only `command_sent`; the integration immediately marks cached
state unavailable and makes all polling tiers due so the normal coordinator
path reconnects and verifies identity. Confirmation phrases reduce accidents
but do not prove physical human presence.

## Identity compatibility

Entity unique IDs use `<verified serial>_<canonical key>`. The serial-backed
device identifier and canonical key are immutable; endpoint, title, authority,
and polling changes do not change entity identity. Changing a key's platform
after release requires an explicit registry/history migration.

The synthetic `<serial>_profile` select is not a register disposition. Its
options are the entry's HA Store profile names and its state is the last fully
successful HA application, never inferred live match. Temporary success is
runtime-only; persistent success also commits the Store marker. Partial apply
does not advance either state.
