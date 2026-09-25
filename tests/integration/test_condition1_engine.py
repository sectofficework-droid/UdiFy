"""End-to-end Condition 1 test: Mock Sheets -> Engine -> real (fixture-
driven) portal adapters -> SQLite audit trail -> Sheet verification.

This is the decision document's own acceptance-requirement shape (§11):

    Student -> Mock Google Sheet -> Workflow Engine -> Mock Government
    Portal -> Portal Result -> Verification -> SQLite Event ->
    Mock Spreadsheet Update -> Spreadsheet Verification -> Final Workflow
    State

Both portals are driven by a REAL local Playwright browser against the
HTML fixtures (not a pure in-memory double) — this is the one test that
proves the whole confirmed Condition 1 pipeline actually works together,
not just each piece in isolation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.condition1 import Condition1Engine
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GREEN, MockSheetsRepository

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
    udise_row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    pen_row = SheetRowRef(spreadsheet="PEN_Entry_(National)", tab="PH2", row_number=5)
    ogr_row = SheetRowRef(spreadsheet="OGR", tab="2026-27", row_number=12)

    student = Student(
        student_id="s-condition1-1",
        name="Aisha Test Student",
        class_name="LKG/KG1/PP2",
        father_name="Test Father",
        mother_name="Test Mother",
        surname="TestSurname",
        dob="02/01/2022",
        udise_row=udise_row,
        pen_row=pen_row,
        ogr_row=ogr_row,
    )
    repo.seed_student(student)

    # UDISE sheet source data — values chosen to exactly match the
    # fixture's limited <select> options (see module docstring in
    # tests/fixtures/gujarat_udise/new_entry.html).
    repo.write_cell(udise_row, "Student Name", "Aisha Test Student")
    repo.write_cell(udise_row, "Father's Name", "Test Father")
    repo.write_cell(udise_row, "Mother's Name", "Test Mother")
    repo.write_cell(udise_row, "Surname", "TestSurname")
    repo.write_cell(udise_row, "Date of Birth", "02/01/2022")
    repo.write_cell(udise_row, "Birth State", "Odisha")
    repo.write_cell(udise_row, "Birth District", "GANJAM")
    repo.write_cell(udise_row, "Birth City", "SHERAGADA")  # doubles as taluka/village — see field_mapping.py
    repo.write_cell(udise_row, "Birth Year", "2022")
    repo.write_cell(udise_row, "Birth Month", "January")
    repo.write_cell(udise_row, "Birth Date", "02")
    repo.write_cell(udise_row, "Birth Cert Reg No", "13/2022")
    repo.write_cell(udise_row, "Mother Tongue", "Odia")

    # PEN sheet source data
    repo.write_cell(pen_row, "Name of Student as per Aadhar Card", "Aisha Test Student")
    repo.write_cell(pen_row, "Mother Tongue", "Odia")
    repo.write_cell(pen_row, "Admission Number in Present School (GR No)", "P091")
    repo.write_cell(pen_row, "Height (cm)", "105")
    repo.write_cell(pen_row, "Weight (kg)", "45")

    return repo, student


def test_condition1_end_to_end_against_fixtures(db_conn, sheets_repo):
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

            engine = Condition1Engine(sheets, gujarat, national, db_conn, environment="MOCK")
            result = engine.run(student, section="A")

            # -- Final workflow state --------------------------------------
            assert result.final_state == "COMPLETE"
            assert result.uid.startswith("24224100067")
            assert result.pen_value == "ND"

            # -- Spreadsheet verification (mock, but genuinely re-read) ---
            udise_values = sheets.get_row_values(student.udise_row)
            assert udise_values["UDISE No"] == result.uid
            assert sheets.get_row_color(student.udise_row) == GREEN

            pen_values = sheets.get_row_values(student.pen_row)
            assert pen_values["PEN"] == "ND"
            assert sheets.get_row_color(student.pen_row) == GREEN

            ogr_values = sheets.get_row_values(student.ogr_row)
            assert ogr_values["UID"] == result.uid
            # OGR row color must NEVER change from gov-entry completion
            # (spec §4.4/§128.4) — confirm it's still the default, not GREEN.
            assert sheets.get_row_color(student.ogr_row) != GREEN

            # -- SQLite audit trail -----------------------------------------
            history = get_case_history(db_conn, student.student_id)
            assert len(history) == 3
            event_codes = [row["event_code"] for row in history]
            assert event_codes == [
                "PEN_ACTION_REQUIRED_OPENED",
                "PEN_VERIFICATION_RESULT",
                "PEN_RESOLVED",
            ]
            assert history[-1]["case_status_after"] == "RESOLVED"
            assert history[-1]["environment"] == "MOCK"
            assert history[-1]["resolution_note"]
            # Tamper-evident chain, same as the isolated events unit tests.
            assert history[1]["previous_event_hash"] == history[0]["event_hash"]
            assert history[2]["previous_event_hash"] == history[1]["event_hash"]
        finally:
            browser.close()
