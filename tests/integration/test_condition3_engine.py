"""End-to-end Condition 3 test: UDISE already imported (precondition) + New PEN.

Condition 3's UDISE half is already resolved before the run starts (spec
§11/§149 — "UDISE already available/imported" is a precondition, not a
live action this run performs). This engine only verifies the UDISE row
is already GREEN, then runs the New PEN branch shared with Condition 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.condition3 import Condition3Engine, UdisePreconditionNotMetError
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GREEN, MockSheetsRepository

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
    udise_row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=7)
    pen_row = SheetRowRef(spreadsheet="PEN_Entry_(National)", tab="PH2", row_number=7)

    student = Student(
        student_id="s-condition3-1",
        name="Priya Test Student",
        class_name="LKG/KG1/PP2",
        father_name="Test Father",
        mother_name="Test Mother",
        surname="TestSurname",
        dob="04/03/2022",
        uid_udise="24224100067ALREADYIMPORTED",
        udise_row=udise_row,
        pen_row=pen_row,
    )
    repo.seed_student(student)

    repo.write_cell(pen_row, "Name of Student as per Aadhar Card", "Priya Test Student")
    repo.write_cell(pen_row, "Mother Tongue", "Odia")
    repo.write_cell(pen_row, "Admission Number in Present School (GR No)", "P100")
    repo.write_cell(pen_row, "Height (cm)", "104")
    repo.write_cell(pen_row, "Weight (kg)", "44")

    return repo, student


def test_condition3_end_to_end_against_fixtures(db_conn, sheets_repo):
    sheets, student = sheets_repo
    sheets.set_row_color(student.udise_row, GREEN)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            national_page = browser.new_page()
            national_page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(national_page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            engine = Condition3Engine(sheets, national, db_conn, environment="MOCK")
            result = engine.run(student)

            assert result.final_state == "COMPLETE"
            assert result.uid == student.uid_udise
            assert result.pen_value == "ND"

            pen_values = sheets.get_row_values(student.pen_row)
            assert pen_values["PEN"] == "ND"
            assert sheets.get_row_color(student.pen_row) == GREEN

            history = get_case_history(db_conn, student.student_id)
            assert history[-1]["case_status_after"] == "RESOLVED"
        finally:
            browser.close()


def test_condition3_raises_when_udise_row_not_green(db_conn, sheets_repo):
    """spec §33.9 Case 2: a known UID is not enough — the row must already
    be GREEN, or this run must not assume UDISE completion."""
    sheets, student = sheets_repo  # row color left at default, never set GREEN

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            national_page = browser.new_page()
            national_page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(national_page, timeout_ms=1000)

            engine = Condition3Engine(sheets, national, db_conn, environment="MOCK")
            with pytest.raises(UdisePreconditionNotMetError):
                engine.run(student)
        finally:
            browser.close()
