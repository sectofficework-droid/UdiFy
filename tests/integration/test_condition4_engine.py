"""End-to-end Condition 4 test: UDISE Import + PEN Import (both pending).

Neither branch resolves the case — this test asserts both end at
ACTION_REQUIRED with the correct pending event codes, never RESOLVED
(Final Authority §J: never mark complete on a submitted request alone).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.condition4 import Condition4Engine
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import LIGHT_ORANGE, MockSheetsRepository

GUJARAT_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "gujarat_udise" / "new_entry.html"
)
NATIONAL_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "udise_plus" / "new_pen_entry.html"
)


@pytest.fixture()
def db_conn(tmp_path):
    conn = connect(tmp_path / "test.sqlite3")
    yield conn
    conn.close()


@pytest.fixture()
def sheets_repo():
    repo = MockSheetsRepository()
    udise_row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=8)
    pen_row = SheetRowRef(spreadsheet="PEN_Entry_(National)", tab="PH2", row_number=8)

    student = Student(
        student_id="s-condition4-1",
        name="Anita Test Student",
        class_name="LKG/KG1/PP2",
        father_name="Test Father",
        mother_name="Test Mother",
        surname="TestSurname",
        dob="05/04/2022",
        aadhaar="999988887777",
        uid_udise="OTHER-SCHOOL-UID-001",
        udise_row=udise_row,
        pen_row=pen_row,
    )
    repo.seed_student(student)
    return repo, student


def test_condition4_end_to_end_against_fixtures(db_conn, sheets_repo):
    sheets, student = sheets_repo

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            gujarat_page = browser.new_page()
            gujarat_page.goto(f"file:///{GUJARAT_FIXTURE.as_posix()}")
            gujarat = GujaratUDISEPortalAdapter(gujarat_page, timeout_ms=3000)
            gujarat.login("24224100067", "not-a-real-password")

            national_page = browser.new_page()
            national_page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(national_page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            engine = Condition4Engine(sheets, gujarat, national, db_conn, environment="MOCK")
            result = engine.run(student)

            assert result.final_state == "BOTH_PENDING"
            assert result.udise_import_status == "REQUEST_SENT"
            assert result.pen_import_info["status"] == "ACTIVE"

            assert sheets.get_row_color(student.udise_row) == LIGHT_ORANGE
            assert sheets.get_row_color(student.pen_row) == LIGHT_ORANGE
            udise_values = sheets.get_row_values(student.udise_row)
            assert udise_values["REMARK"] == "REQUEST SENT"
            pen_values = sheets.get_row_values(student.pen_row)
            assert pen_values["REMARK"] == "IMPORT PENDING"

            history = get_case_history(db_conn, student.student_id)
            event_codes = [row["event_code"] for row in history]
            assert event_codes == [
                "UDISE_REQUEST_SENT_OTHER_SCHOOL",
                "IMPORT_PENDING_ACTIVE_OTHER_SCHOOL",
            ]
            assert all(row["case_status_after"] == "ACTION_REQUIRED" for row in history)
        finally:
            browser.close()
