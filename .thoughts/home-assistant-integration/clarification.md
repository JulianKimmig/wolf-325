# Home Assistant Integration

Purpose: Clarification questions, user answers, and resolved assumptions.

## Source Task

Clarifications for the Home Assistant integration planning task captured in
`perspectives.md`.

## Chain-of-Thought Summary

- The user selected a native HACS/manual custom integration as the first
  distribution target, while keeping the design compatible with a possible
  future Home Assistant Core contribution.
- Runtime authority is a per-device choice with monitor-only, temporary, and
  persistent modes rather than one global write policy.
- Profile capture must initially preserve the TUI contract: save persistent
  desired-setting deltas and lineage, not a snapshot of arbitrary live values.
- Home Assistant owns its profile storage; direct cross-process sharing with
  CLI/TUI files is outside the initial boundary.
- All supported datapoints may have entity definitions, but the default surface
  is curated and dangerous communication/reset operations are excluded from
  ordinary entities.
- Multiple devices and configurable polling intervals measured in seconds are
  first-release requirements.
- The user requested four reasoning agents for the solution round.

## Findings

- **Distribution:** HACS/manual custom integration first; preserve a path to
  Core compatibility.
- **Control modes:** monitor-only, temporary, and persistent, configurable per
  device/config entry.
- **Profile capture:** exact TUI behavior initially.
- **Profile storage:** Home Assistant-owned storage.
- **Entity policy:** define all supported datapoints, curate defaults, omit
  dangerous Modbus configuration and appliance-reset controls from ordinary
  entities, and use guarded actions only where appropriate.
- **Scale and cadence:** support multiple devices from the start and make
  polling configurable in seconds.
- **Reasoning round:** four agents. Three will run concurrently and the fourth
  will run immediately afterward because the active workspace has three child
  slots.

## Questions and Answers

1. **Target distribution?** HACS/manual custom integration: **yes**.
2. **Control authority?** Configurable monitor-only, temporary, and persistent
   modes.
3. **Capture semantics?** Exact TUI behavior initially.
4. **Profile storage?** Home Assistant-owned storage.
5. **Entity and dangerous-operation policy?** All supported datapoints may be
   exposed; use curated defaults; omit dangerous Modbus configuration/reset
   controls from ordinary entities and expose guarded actions only where
   appropriate.
6. **Multiple devices and polling?** Multiple devices from the first release,
   with configurable polling intervals in seconds.
7. **Reasoning agents?** Four.

## Running Log

- Session file created.
- Initial perspective analysis completed.
- User clarification answers recorded.
- Four-agent reasoning round authorized.
