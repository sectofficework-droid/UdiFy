"""Tests for src/portals/base.py's generic, portal-agnostic
set_file_input()/wait_for_dependent_option() helpers.

These are NOT adapter methods and are not wired into any condition
branch — see base.py's module-level note. This only proves the two
Playwright mechanics work correctly in isolation, against a synthetic
fixture that models neither real portal.
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from src.portals.base import set_file_input, wait_for_dependent_option

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "generic"
    / "file_upload_and_dependent_dropdown.html"
)


def test_set_file_input_uploads_by_label(tmp_path):
    upload_file = tmp_path / "document.txt"
    upload_file.write_text("test content")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{FIXTURE.as_posix()}")

            set_file_input(page, "Upload Document", upload_file)

            files = page.eval_on_selector(
                "#upload", "el => Array.from(el.files).map(f => f.name)"
            )
            assert files == ["document.txt"]
        finally:
            browser.close()


def test_wait_for_dependent_option_waits_for_async_population():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{FIXTURE.as_posix()}")

            page.get_by_label("State").select_option(label="Odisha")
            # The District options populate 300ms after the state changes —
            # selecting immediately (without waiting) would fail since the
            # option doesn't exist yet.
            wait_for_dependent_option(page, "District", "GANJAM", timeout_ms=2000)

            selected = page.eval_on_selector("#district", "el => el.value")
            assert selected == "GANJAM"
        finally:
            browser.close()


def test_wait_for_dependent_option_picks_the_correct_state_specific_option():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{FIXTURE.as_posix()}")

            page.get_by_label("State").select_option(label="Gujarat")
            wait_for_dependent_option(page, "District", "SURAT", timeout_ms=2000)

            selected = page.eval_on_selector("#district", "el => el.value")
            assert selected == "SURAT"
        finally:
            browser.close()
