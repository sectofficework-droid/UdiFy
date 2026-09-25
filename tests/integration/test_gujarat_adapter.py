"""Integration test: GujaratUDISEPortalAdapter against a local HTML fixture.

This exercises the REAL adapter code (real Playwright locators) against a
fixture page, not an in-memory Python double — the point is to actually
validate the selector strategy, not just the workflow-engine orchestration
logic (that's what the unit tests + a lightweight mock adapter, added
alongside the remaining portal branches, are for).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.portals.udise_gujarat.adapter import (
    CtsDetails,
    GujaratUDISEPortalAdapter,
    ManualBirthDetails,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "gujarat_udise" / "new_entry.html"
)


@pytest.fixture()
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        pg.goto(f"file:///{FIXTURE_PATH.as_posix()}")
        yield pg
        browser.close()


def test_full_new_entry_flow_against_fixture(page):
    adapter = GujaratUDISEPortalAdapter(page, timeout_ms=3000)

    adapter.login("24224100067", "not-a-real-password")
    adapter.open_student_new_entry()

    adapter.submit_manual_birth_details(
        ManualBirthDetails(
            birth_state="Odisha",
            birth_district="GANJAM",
            birth_taluka="SHERAGADA",
            birth_city_or_place="Sheragada",
            birth_village="Sheragada",
            year="2022",
            month="January",
            date="02",
            brn_present=True,
            brn_no="13/2022",
        )
    )

    adapter.submit_cts_details(
        CtsDetails(
            student_name="Test Student One",
            father_name="Test Father",
            mother_name="Test Mother",
            surname="One",
            dob="02/01/2022",
        )
    )

    adapter.open_student_profile("Test Student One")
    adapter.open_tab("Personal")
    adapter.fill_tab({"Mother Tongue": "Odia", "Category": "General"})
    adapter.save_current_tab()

    # Real assertion against the real (fixture) DOM state, not an assumption.
    from playwright.sync_api import expect

    expect(page.get_by_text("Student saved successfully.")).to_be_visible()


def test_udise_import_transfer_request_flow_against_fixture(page):
    """UDISE Import / transfer-request confirmed pending outcome (spec §X):
    other-school student found -> Confirm -> Transfer Student page ->
    Update Transfer Request -> success message. Mock scenario checklist
    items: Existing student search, Other-school student found, Transfer
    confirmation, Transfer Student page, Transfer From/To, success message."""
    adapter = GujaratUDISEPortalAdapter(page, timeout_ms=3000)
    adapter.login("24224100067", "not-a-real-password")

    found = adapter.search_existing_student_by_uid("LKG/KG1/PP2", "OTHER-SCHOOL-UID-001")
    assert found is True

    result = adapter.confirm_transfer_request()
    assert result == "Student Transfer request saved successfully."


def test_udise_import_search_no_match_returns_false(page):
    """Mock scenario: searching a UID with no other-school match must
    return False, never guess a match (spec §300)."""
    adapter = GujaratUDISEPortalAdapter(page, timeout_ms=300)
    adapter.login("24224100067", "not-a-real-password")

    found = adapter.search_existing_student_by_uid("LKG/KG1/PP2", "NO-SUCH-UID")
    assert found is False


def test_verification_failure_raises_rather_than_assuming_success(page):
    """spec Final Authority §D: never assume success from a click alone —
    if the expected resulting state genuinely never appears, the adapter
    must raise, not silently continue. Exercises _verify_visible directly
    against text that will never be on the loaded fixture page, which is
    the actual mechanism every public method above relies on."""
    from src.portals.base import ConsequentialActionUnverifiedError

    adapter = GujaratUDISEPortalAdapter(page, timeout_ms=300)
    with pytest.raises(ConsequentialActionUnverifiedError):
        adapter._verify_visible(
            page.get_by_text("This text is not on the fixture page"),
            "Expected text that will never appear",
        )
