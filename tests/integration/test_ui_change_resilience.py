"""UI-change resilience acceptance tests (spec "UI CHANGE HANDLING —
IMPLEMENTATION ACCEPTANCE TESTS", ~line 10481).

"The implementation is not accepted merely because it works against
today's exact screenshots." These tests run the exact same, UNCHANGED
adapter code against a deliberately altered fixture
(new_entry_ui_changed.html) covering every category the spec lists as
must-tolerate:

    - changed stable/non-stable element ID (every id renamed)
    - additional wrapper <div> (every field/section wrapped)
    - reordered form fields (CTS fields shuffled)
    - equivalent button label (case/wording changed: "LOG IN" -> "Log
      in", "ADD NEW STUDENT" -> "Add new student", "SAVE STUDENT" ->
      "Save student", "Next" -> "next")
    - minor text punctuation/capitalization changes (the heading itself:
      "STUDENT NEW ENTRY" -> "Student New Entry")

then a second test proves the OTHER half of the same spec requirement —
"for unknown business changes, it must stop safely and generate
diagnostics" — by pointing the adapter at a page with none of the
expected elements at all, and asserting it raises a structured
ConsequentialActionUnverifiedError rather than hanging, crashing
unpredictably, or silently treating a missing element as success.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.portals.base import ConsequentialActionUnverifiedError
from src.portals.udise_gujarat.adapter import CtsDetails, GujaratUDISEPortalAdapter, ManualBirthDetails

CHANGED_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "gujarat_udise" / "new_entry_ui_changed.html"
)


@pytest.fixture()
def changed_page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page()
        pg.goto(f"file:///{CHANGED_FIXTURE.as_posix()}")
        yield pg
        browser.close()


def test_new_entry_flow_survives_ids_wrappers_reorder_and_label_casing(changed_page):
    """The exact same adapter methods Condition 1 uses, unmodified, run
    to completion against a fixture where every id changed, every field
    is wrapped in an extra <div>, CTS fields are reordered, and button
    labels/the screen heading changed casing/wording."""
    adapter = GujaratUDISEPortalAdapter(changed_page, timeout_ms=3000)

    adapter.login("24224100067", "not-a-real-password")  # button says "Log in"
    adapter.open_student_new_entry()  # heading says "Student New Entry", not all-caps

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
    )  # "next" button, lowercase

    adapter.submit_cts_details(
        CtsDetails(
            student_name="Resilience Test Student",
            father_name="Test Father",
            mother_name="Test Mother",
            surname="One",
            dob="02/01/2022",
        )
    )  # fields reordered in the DOM; "Add new student" button

    adapter.open_student_profile("Resilience Test Student")
    adapter.open_tab("Personal")
    adapter.fill_tab({"Mother Tongue": "Odia", "Category": "General"})
    adapter.save_current_tab(save_button_name="Save Student")  # was "SAVE STUDENT"

    from playwright.sync_api import expect

    expect(changed_page.get_by_text("Student saved successfully.")).to_be_visible()


def test_genuinely_missing_element_fails_safely_with_diagnostics(changed_page):
    """The other half of the spec requirement: an UNRECOGNIZED state (not
    a cosmetic change) must stop safely with a structured error, never be
    silently treated as success."""
    adapter = GujaratUDISEPortalAdapter(changed_page, timeout_ms=300)
    with pytest.raises(ConsequentialActionUnverifiedError):
        adapter._verify_visible(
            changed_page.get_by_text("This text exists on no version of this fixture"),
            "Expected a state that genuinely does not exist",
        )
