"""Headless Textual interaction tests for the complete controller TUI."""

from __future__ import annotations

import json

import pytest
from textual.widgets import Button, DataTable, Input, Static, Switch, Tree

from wolf_325.catalogue import REGISTERS
from wolf_325.tui_app import WolfCWL2App
from wolf_325.tui_navigation import REGISTER_SECTIONS


@pytest.mark.asyncio
async def test_app_mounts_detailed_navigation_and_live_overview(
    controller: tuple[object, object],
) -> None:
    """The initial screen exposes status, domain menus, values, and details."""
    instance, _ = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=0.05,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        await pilot.pause()
        tree = app.query_one("#navigation", Tree)
        table = app.query_one("#register-table", DataTable)
        status = app.query_one("#connection-status", Static)

        assert len(list(tree.root.children)) >= 4
        assert table.row_count > 0
        assert "Connected" in str(status.render())
        assert app.query_one("#edit", Button).disabled is True


@pytest.mark.asyncio
async def test_redraw_tick_is_inert_after_application_unmount(
    controller: tuple[object, object],
) -> None:
    """Ignore an already-queued timer callback after widgets are removed."""
    instance, _ = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)):
        app._tick()

    app._tick()


@pytest.mark.asyncio
async def test_redraw_tick_is_inert_during_widget_teardown(
    controller: tuple[object, object],
) -> None:
    """Ignore a queued timer after teardown removes a required root widget."""
    instance, _ = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=60,
        background=False,
    )

    async with app.run_test(size=(180, 52)):
        await app.query_one("#connection-status", Static).remove()
        app._tick()


@pytest.mark.asyncio
async def test_all_view_and_search_cover_complete_catalogue(
    controller: tuple[object, object],
) -> None:
    """The all-register view contains every value and filters immediately."""
    instance, _ = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        await app.show_view("all")
        await pilot.pause()
        table = app.query_one("#register-table", DataTable)
        assert table.row_count == len(REGISTERS)

        app.query_one("#search", Input).value = "remote airflow"
        await pilot.pause()
        assert table.row_count == 1
        assert app.visible_register_keys == ("remote_airflow_m3h",)


@pytest.mark.asyncio
async def test_domain_view_selection_and_cursor_update_register_details(
    controller: tuple[object, object],
) -> None:
    """Selecting a submenu and row updates the table and metadata panel."""
    instance, _ = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        await app.show_view("section:remote-control")
        await pilot.pause()
        expected = next(
            section.register_keys
            for section in REGISTER_SECTIONS
            if section.section_id == "remote-control"
        )
        assert app.visible_register_keys == expected

        app.query_one("#register-table", DataTable).move_cursor(row=2)
        await pilot.pause()
        details = str(app.query_one("#register-details", Static).render())
        assert "remote_airflow_m3h" in details
        assert app.query_one("#edit", Button).disabled is False


@pytest.mark.asyncio
async def test_read_only_app_disables_modifying_controls(
    controller: tuple[object, object],
) -> None:
    """Read-only mode keeps refresh available but disables every write control."""
    instance, _ = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=True,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        await app.show_view("section:remote-control")
        app.query_one("#register-table", DataTable).move_cursor(row=2)
        await pilot.pause()

        assert app.query_one("#edit", Button).disabled is True
        assert app.query_one("#release", Button).disabled is True
        assert app.query_one("#profiles", Button).disabled is True
        assert app.query_one("#save-profile", Button).disabled is True
        assert app.query_one("#refresh", Button).disabled is False


@pytest.mark.asyncio
async def test_numeric_editor_submits_temporary_write_from_toolbar(
    controller: tuple[object, object],
) -> None:
    """The complete row-to-modal workflow writes validated values to the device."""
    instance, client = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        await app.show_view("section:remote-control")
        app.query_one("#register-table", DataTable).move_cursor(row=2)
        await pilot.pause()
        assert app._selected_key == "remote_airflow_m3h"
        assert app.query_one("#edit", Button).disabled is False
        assert await pilot.click("#edit") is True
        await pilot.pause()

        app.screen.query_one("#editor-input", Input).value = "200"
        app.screen.query_one("#editor-persist", Switch).value = False
        await pilot.click("#submit")
        await app.workers.wait_for_complete()

        assert (8002, 200, 20) in client.writes  # type: ignore[attr-defined]
        assert instance.desired == {}  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_numeric_editor_keeps_invalid_value_off_the_device(
    controller: tuple[object, object],
) -> None:
    """An invalid modal value stays visible as an error and causes no write."""
    instance, client = controller
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        await app.show_view("section:remote-control")
        app.query_one("#register-table", DataTable).move_cursor(row=2)
        await pilot.pause()
        assert await pilot.click("#edit") is True
        await pilot.pause()

        app.screen.query_one("#editor-input", Input).value = "326"
        assert await pilot.click("#submit") is True
        await pilot.pause()

        error = str(app.screen.query_one("#editor-error", Static).render())
        assert "above maximum 325" in error
        assert client.writes == []  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_save_profile_dialog_writes_derived_profile(
    controller: tuple[object, object], config_path: Path
) -> None:
    """The toolbar dialog previews and saves the current desired-state delta."""
    (config_path.parent / "profiles" / "base.json").write_text(
        '{"settings":{"remote_airflow_m3h":100}}', encoding="utf-8"
    )
    instance, _ = controller
    desired = await instance.config_store.update_desired(  # type: ignore[attr-defined]
        {"remote_airflow_m3h": 200}, replace=True, last_profile="base"
    )
    instance.config["desired"] = desired  # type: ignore[index]
    instance.config["last_profile"] = "base"  # type: ignore[index]
    app = WolfCWL2App(
        controller=instance,  # type: ignore[arg-type]
        read_only=False,
        refresh_interval=1,
        background=False,
    )

    async with app.run_test(size=(180, 52)) as pilot:
        assert await pilot.click("#save-profile") is True
        await pilot.pause()
        preview = str(
            app.screen.query_one("#save-profile-preview", Static).render()
        )
        assert "Base profile: base" in preview
        app.screen.query_one("#profile-name", Input).value = "derived"
        app.screen.query_one("#profile-description", Input).value = "Saved in TUI"
        assert await pilot.click("#save-profile-submit") is True
        await app.workers.wait_for_complete()

    document = json.loads(
        (config_path.parent / "profiles" / "derived.json").read_text(encoding="utf-8")
    )
    assert document["extends"] == "base"
    assert document["settings"] == {"remote_airflow_m3h": 200}
