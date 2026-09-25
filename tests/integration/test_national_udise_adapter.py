"""Integration test: NationalUDISEPortalAdapter against a local HTML fixture.

Real Playwright locators against a fixture page — same rationale as
tests/integration/test_gujarat_adapter.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from src.portals.base import AutomationPausedForUser
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter, NewStudentInit

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "udise_plus" / "new_pen_entry.html"
)


def _make_page(pw, query: str = ""):
    browser = pw.chromium.launch()
    page = browser.new_page()
    url = f"file:///{FIXTURE_PATH.as_posix()}"
    if query:
        url += f"?{query}"
    page.goto(url)
    return browser, page


def test_full_new_pen_entry_flow_without_consent_required():
    with sync_playwright() as pw:
        browser, page = _make_page(pw)
        try:
            adapter = NationalUDISEPortalAdapter(page, timeout_ms=3000)
            adapter.login("sunil.pradhan", "not-a-real-password")

            adapter.initialize_new_student(
                NewStudentInit(student_name="Test Student Two", class_name="LKG/KG1/PP2", section="A")
            )
            adapter.go_to_fill_general_profile()

            adapter.fill_general_profile(
                {"Guardian's Name": "Test Guardian", "Mother Tongue of Student": "Odia"}
            )
            adapter.proceed_from_general_profile()
            assert adapter.check_aadhaar_consent_required() is False

            adapter.fill_enrolment_profile({"Admission Number in Present School": "P099"})
            adapter.fill_facility_profile(
                {"Student's Height (in CMS)": "105", "Student's Weight (in KGS)": "45"}
            )
            result = adapter.complete_profile_preview()
            assert result == "Data completion is complete."
        finally:
            browser.close()


def test_aadhaar_consent_pauses_and_is_never_auto_clicked():
    """spec §39/§142/§I: the adapter must NEVER click "I Agree" itself.

    The fixture is toggled (via ?consent=1) so General Profile's Next
    reveals the consent dialog instead of advancing — this is the fixture
    standing in for the real portal's documented behavior. The test
    proves the adapter detects it and does not proceed on its own.
    """
    with sync_playwright() as pw:
        browser, page = _make_page(pw, query="consent=1")
        try:
            adapter = NationalUDISEPortalAdapter(page, timeout_ms=1500)
            adapter.login("sunil.pradhan", "x")
            adapter.initialize_new_student(
                NewStudentInit(student_name="Test Student Three", class_name="LKG/KG1/PP2", section="A")
            )
            adapter.go_to_fill_general_profile()
            adapter.fill_general_profile({"Guardian's Name": "G", "Mother Tongue of Student": "Odia"})
            adapter.proceed_from_general_profile()

            assert adapter.check_aadhaar_consent_required() is True
            # Confirm the page genuinely did NOT advance to Enrolment Profile —
            # the adapter must not have clicked past the block itself.
            expect(page.get_by_text("CONSENT FOR DEMOGRAPHIC AUTHENTICATION")).to_be_visible()
            expect(page.locator("#screen-enrolment")).to_be_hidden()

            # Confirm the adapter provides no method that clicks "I Agree" —
            # this is a workflow-engine/operator decision, never automated
            # here. (Structural check: the fixture's own button exists and
            # is untouched by anything the adapter did.)
            expect(page.locator("#i-agree-btn")).to_be_visible()
        finally:
            browser.close()
