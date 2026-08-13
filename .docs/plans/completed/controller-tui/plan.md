# Controller TUI implementation plan

## Objective

Add a first-class `wolf-cwl2-tui` terminal application that can monitor every
catalogued register and operate every writable register without duplicating
Modbus addresses, codecs, validation constraints, or persistence semantics.

## User experience

- Show connection state, poll timestamps, desired-state ownership, errors, and
  live values in one keyboard-friendly layout.
- Organize all registers into domain menus and submenus, with additional
  overview, all-register, writable, desired, and problem views.
- Provide search, immediate refresh, live background updates, register details,
  enum/boolean/numeric editors, temporary versus persistent writes, profiles,
  and guarded one-shot actions.
- Keep communication-setting and appliance-reset operations behind an explicit
  confirmation phrase because a successful write can disconnect the session.
- Support a command-line read-only mode that disables every modifying action.

## Architecture

1. `tui_navigation.py` owns the stable domain taxonomy and derives register
   membership from the canonical catalogue.
2. `tui_models.py` converts controller snapshots and register definitions into
   presentation rows, details, filters, and editor specifications.
3. `tui_dialogs.py` owns write and profile modal screens.
4. `tui_app.py` owns the Textual layout, controller lifecycle, workers, and UI
   event handling.
5. `tui.py` is the small command-line entry point.

The existing `WolfCWL2` API remains the only route for device reads, writes,
desired-state persistence, validation, profiles, and guarded reset actions.

## Test sequence

1. Assert the taxonomy partitions the entire catalogue exactly once.
2. Assert filtering, formatting, detail metadata, and editor specifications.
3. Exercise the app with Textual's headless pilot and the existing external
   Modbus simulator.
4. Exercise successful writes, rejected values, read-only behavior, dangerous
   confirmations, profile previews/applications, and connection errors.
5. Run the full test suite, package build, entry-point help, and source line
   length checks.

## Documentation ownership

- `.docs/ARCHITECTURE.md`: package and dependency boundaries.
- `.docs/code-relationships.md`: TUI-to-controller/test relationships.
- `.docs/contracts/controller-api-and-json.md`: executable entry point and
  interaction contract.
- `.docs/workflows/tui-operation.md`: operator workflow and safety model.

## Completion evidence

- The catalogue taxonomy assigns all 154 definitions exactly once.
- Headless Textual tests cover navigation, all-register search, selection,
  read-only controls, valid writes, and invalid editor values.
- Controller-backed tests cover temporary/persistent writes, ownership release,
  profiles, one-shot actions, and dangerous/read-only guards.
- The complete suite passes with 144 tests and two opt-in physical tests skipped.
- Both source and wheel builds succeed; the wheel contains `tui.tcss` and the
  `wolf-cwl2-tui` console entry point.
