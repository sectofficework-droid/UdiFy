"""End-to-end ND Reconciliation test (spec §165/§259-264), against the
National UDISE+ fixture's ND-reconciliation search mode."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.nd_reconciliation import (
    AMBIGUOUS_MANUAL_REVIEW,
    PEN_FOUND,
    STILL_ND,
    run_nd_reconciliation,
)
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
def national():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
        adapter = NationalUDISEPortalAdapter(page, timeout_ms=3000)
        adapter.login("sunil.pradhan", "not-a-real-password")
        yield adapter
        browser.close()


def _resolved_student(name: str, dob: str, student_id: str) -> tuple[MockSheetsRepository, Student]:
    sheets = MockSheetsRepository()
    pen_row = SheetRowRef(spreadsheet="PEN_Entry_(National)", tab="PH2", row_number=10)
    ogr_row = SheetRowRef(spreadsheet="OGR", tab="2026-27", row_number=20)
    student = Student(
        student_id=student_id, name=name, class_name="LKG/KG1/PP2", dob=dob,
        pen="ND", pen_row=pen_row, ogr_row=ogr_row,
    )
    sheets.seed_student(student)
    sheets.write_cell(pen_row, "PEN", "ND")
    sheets.write_cell(ogr_row, "PEN", "ND")
    return sheets, student


def test_actual_pen_found_updates_sheet_and_ogr_and_resolves_case(db_conn, national):
    sheets, student = _resolved_student("Test ND Student One", "02/01/2022", "s-nd-1")

    outcome = run_nd_reconciliation(
        national, sheets, db_conn, student, class_name="LKG/KG1/PP2", environment="MOCK",
    )

    assert outcome == PEN_FOUND
    assert sheets.get_row_values(student.pen_row)["PEN"] == "23613114903"
    assert sheets.get_row_color(student.pen_row) == GREEN
    assert sheets.get_row_values(student.ogr_row)["PEN"] == "23613114903"

    history = get_case_history(db_conn, student.student_id)
    assert [row["event_code"] for row in history] == [
        "PEN_CASE_REOPENED",
        "PEN_REOPEN_VERIFICATION",
        "PEN_RESOLVED",
    ]
    assert history[-1]["case_status_after"] == "RESOLVED"
    assert history[-1]["pen"] == "23613114903"
    # Tamper-evident hash chain continues correctly into the new cycle.
    assert history[1]["previous_event_hash"] == history[0]["event_hash"]
    assert history[2]["previous_event_hash"] == history[1]["event_hash"]


def test_no_actual_pen_keeps_nd(db_conn, national):
    sheets, student = _resolved_student("Test ND Student Two", "03/02/2022", "s-nd-2")

    outcome = run_nd_reconciliation(
        national, sheets, db_conn, student, class_name="LKG/KG1/PP2", environment="MOCK",
    )

    assert outcome == STILL_ND
    assert sheets.get_row_values(student.pen_row)["PEN"] == "ND"
    assert get_case_history(db_conn, student.student_id) == []


def test_ambiguous_match_routes_to_manual_review_without_writing_sheet(db_conn, national):
    sheets, student = _resolved_student("Test ND Ambiguous", "09/09/2022", "s-nd-3")

    outcome = run_nd_reconciliation(
        national, sheets, db_conn, student, class_name="LKG/KG1/PP2", environment="MOCK",
    )

    assert outcome == AMBIGUOUS_MANUAL_REVIEW
    assert sheets.get_row_values(student.pen_row)["PEN"] == "ND"

    history = get_case_history(db_conn, student.student_id)
    assert [row["event_code"] for row in history] == [
        "PEN_CASE_REOPENED",
        "PEN_STUDENT_MATCH_AMBIGUOUS",
    ]
    assert history[-1]["case_status_after"] == "MANUAL_REVIEW"
