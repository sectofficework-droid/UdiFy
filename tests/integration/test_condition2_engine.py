"""End-to-end Condition 2 test: New UDISE + PEN Import.

Mirrors test_condition1_engine.py's shape but the PEN half is the
confirmed PEN Import — Other School ACTIVE workflow, which must end in
ACTION_REQUIRED/IMPORT PENDING, never RESOLVED (Final Authority §J).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.condition2 import Condition2Engine
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GREEN, LIGHT_ORANGE, MockSheetsRepository

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
    udise_row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=6)
    pen_row = SheetRowRef(spreadsheet="PEN_Entry_(National)", tab="PH2", row_number=6)

    student = Student(
        student_id="s-condition2-1",
        name="Rahul Test Student",
        class_name="LKG/KG1/PP2",
        father_name="Test Father",
        mother_name="Test Mother",
        surname="TestSurname",
        dob="03/02/2022",
        aadhaar="999988887777",
        udise_row=udise_row,
        pen_row=pen_row,
    )
    repo.seed_student(student)

    repo.write_cell(udise_row, "Student Name", "Rahul Test Student")
    repo.write_cell(udise_row, "Father's Name", "Test Father")
    repo.write_cell(udise_row, "Mother's Name", "Test Mother")
    repo.write_cell(udise_row, "Surname", "TestSurname")
    repo.write_cell(udise_row, "Date of Birth", "03/02/2022")
    repo.write_cell(udise_row, "Birth State", "Odisha")
    repo.write_cell(udise_row, "Birth District", "GANJAM")
    repo.write_cell(udise_row, "Birth City", "SHERAGADA")
    repo.write_cell(udise_row, "Birth Year", "2022")
    repo.write_cell(udise_row, "Birth Month", "January")
    repo.write_cell(udise_row, "Birth Date", "02")
    repo.write_cell(udise_row, "Birth Cert Reg No", "14/2022")
    repo.write_cell(udise_row, "Mother Tongue", "Odia")

    return repo, student


def test_condition2_end_to_end_against_fixtures(db_conn, sheets_repo):
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

            engine = Condition2Engine(sheets, gujarat, national, db_conn, environment="MOCK")
            result = engine.run(student)

            assert result.final_state == "UDISE_COMPLETE_PEN_PENDING"
            assert result.uid.startswith("24224100067")
            assert result.pen_import_info["status"] == "ACTIVE"

            assert sheets.get_row_color(student.udise_row) == GREEN
            assert sheets.get_row_color(student.pen_row) == LIGHT_ORANGE
            pen_values = sheets.get_row_values(student.pen_row)
            assert pen_values["REMARK"] == "IMPORT PENDING"

            history = get_case_history(db_conn, student.student_id)
            assert history[-1]["event_code"] == "IMPORT_PENDING_ACTIVE_OTHER_SCHOOL"
            assert history[-1]["case_status_after"] == "ACTION_REQUIRED"
        finally:
            browser.close()
