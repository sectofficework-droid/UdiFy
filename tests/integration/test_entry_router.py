"""End-to-end test: run_entry() determines the condition from real sheet
state and dispatches to the matching engine — closing the previously
honestly-flagged "no automated entry-condition routing" gap."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.engine.entry_router import AmbiguousEntryConditionError, run_entry
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
def portals():
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

            yield gujarat, national
        finally:
            browser.close()


def test_run_entry_auto_routes_to_condition_1_from_sheet_state(db_conn, portals):
    gujarat, national = portals
    sheets = MockSheetsRepository()
    udise_row = SheetRowRef("UDISE_Entry_(State)", "PH2", 5)
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 5)
    ogr_row = SheetRowRef("OGR", "2026-27", 12)
    student = Student(
        student_id="s-router-c1", name="Router Condition1 Student", class_name="LKG/KG1/PP2",
        father_name="Test Father", mother_name="Test Mother", surname="TestSurname",
        dob="02/01/2022", udise_row=udise_row, pen_row=pen_row, ogr_row=ogr_row,
    )
    sheets.seed_student(student)
    sheets.write_cell(udise_row, "Student Name", student.name)
    sheets.write_cell(udise_row, "Father's Name", "Test Father")
    sheets.write_cell(udise_row, "Mother's Name", "Test Mother")
    sheets.write_cell(udise_row, "Surname", "TestSurname")
    sheets.write_cell(udise_row, "Date of Birth", "02/01/2022")
    sheets.write_cell(udise_row, "Birth State", "Odisha")
    sheets.write_cell(udise_row, "Birth District", "GANJAM")
    sheets.write_cell(udise_row, "Birth City", "SHERAGADA")
    sheets.write_cell(udise_row, "Birth Year", "2022")
    sheets.write_cell(udise_row, "Birth Month", "January")
    sheets.write_cell(udise_row, "Birth Date", "02")
    sheets.write_cell(pen_row, "Name of Student as per Aadhar Card", student.name)

    # No pre-supplied "which condition" hint anywhere — run_entry derives
    # it purely from the sheet state above (both sides NEW -> Condition 1).
    result = run_entry(sheets, gujarat, national, db_conn, student, environment="MOCK")

    assert result is not None
    assert result.final_state == "COMPLETE"
    assert sheets.get_row_color(udise_row) == GREEN
    assert sheets.get_row_color(pen_row) == GREEN


def test_run_entry_skips_an_already_complete_student(db_conn, portals):
    gujarat, national = portals
    sheets = MockSheetsRepository()
    udise_row = SheetRowRef("UDISE_Entry_(State)", "PH2", 6)
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 6)
    student = Student(
        student_id="s-router-done", name="Already Done Student", class_name="LKG/KG1/PP2",
        udise_row=udise_row, pen_row=pen_row,
    )
    sheets.seed_student(student)
    sheets.set_row_color(udise_row, GREEN)
    sheets.set_row_color(pen_row, GREEN)

    result = run_entry(sheets, gujarat, national, db_conn, student, environment="MOCK")

    assert result is None  # never touched the portals


def test_run_entry_raises_for_an_ambiguous_state_rather_than_guessing(db_conn, portals):
    gujarat, national = portals
    sheets = MockSheetsRepository()
    udise_row = SheetRowRef("UDISE_Entry_(State)", "PH2", 7)
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 7)
    student = Student(
        student_id="s-router-ambiguous", name="Ambiguous Student", class_name="LKG/KG1/PP2",
        aadhaar="999988887777", udise_row=udise_row, pen_row=pen_row,
    )
    sheets.seed_student(student)
    sheets.set_row_color(udise_row, GREEN)  # already complete...
    # ...but PEN carries the Aadhaar-import signal, not a defined combination.

    with pytest.raises(AmbiguousEntryConditionError):
        run_entry(sheets, gujarat, national, db_conn, student, environment="MOCK")
