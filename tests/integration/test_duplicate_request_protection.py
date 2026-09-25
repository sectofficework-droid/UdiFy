"""Duplicate-submission protection tests (spec AI-operating-instructions
#19: "Never duplicate a transfer request because a confirmation response
was lost"). Each test calls the same branch/function TWICE for the same
student and proves the second call never touches the portal again — it
recognizes the existing open request_cases row and returns without
resubmitting."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.request_cases import find_open_request_case
from src.engine.branches import run_pen_import_branch, run_udise_import_branch
from src.engine.release_request import generate_pen_release_request
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter, ReleaseAdmissionDetail
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import MockSheetsRepository

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


def test_udise_import_branch_never_resubmits_a_transfer_request(db_conn):
    sheets = MockSheetsRepository()
    udise_row = SheetRowRef("UDISE_Entry_(State)", "PH2", 5)
    student = Student(
        student_id="s-dup-udise", name="Dup UDISE Student", class_name="LKG/KG1/PP2",
        uid_udise="OTHER-SCHOOL-UID-001", udise_row=udise_row,
    )
    sheets.seed_student(student)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{GUJARAT_FIXTURE.as_posix()}")
            gujarat = GujaratUDISEPortalAdapter(page, timeout_ms=3000)
            gujarat.login("24224100067", "not-a-real-password")

            first = run_udise_import_branch(
                gujarat, sheets, db_conn, student, class_name="LKG/KG1/PP2", environment="MOCK",
            )
            assert first == "REQUEST_SENT"

            # Second call for the SAME student: the fixture's transfer
            # confirmation dialog only exists once per page load, so if
            # this call tried to submit again it would fail outright —
            # instead it must recognize the existing case and skip.
            second = run_udise_import_branch(
                gujarat, sheets, db_conn, student, class_name="LKG/KG1/PP2", environment="MOCK",
            )
            assert second == "REQUEST_SENT"
        finally:
            browser.close()

    cases = db_conn.execute(
        "SELECT COUNT(*) FROM request_cases WHERE student_id = ?", (student.student_id,)
    ).fetchone()[0]
    assert cases == 1  # never created a second row


def test_pen_import_branch_never_rechecks_after_first_success(db_conn):
    sheets = MockSheetsRepository()
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 5)
    student = Student(
        student_id="s-dup-pen", name="Dup PEN Student", class_name="LKG/KG1/PP2",
        aadhaar="999988887777", pen_row=pen_row,
    )
    sheets.seed_student(student)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            first = run_pen_import_branch(national, sheets, db_conn, student, environment="MOCK")
            assert first["status"] == "ACTIVE"

            second = run_pen_import_branch(national, sheets, db_conn, student, environment="MOCK")
            assert second["status"] == "ACTIVE"
        finally:
            browser.close()

    cases = db_conn.execute(
        "SELECT COUNT(*) FROM request_cases WHERE student_id = ?", (student.student_id,)
    ).fetchone()[0]
    assert cases == 1


def test_generate_pen_release_request_never_resubmits(db_conn):
    sheets = MockSheetsRepository()
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 9)
    student = Student(
        student_id="s-dup-release", name="Test Release Student", class_name="LKG/KG1/PP2",
        pen_row=pen_row,
    )
    sheets.seed_student(student)
    admission = ReleaseAdmissionDetail(
        class_name="LKG/KG1/PP2", section="A", admission_date="01/06/2026",
        remark="Please release the student from the school records",
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            first_id = generate_pen_release_request(
                national, sheets, db_conn, student,
                pen="23428960733", dob="03/02/2022", admission=admission, environment="MOCK",
            )
            second_id = generate_pen_release_request(
                national, sheets, db_conn, student,
                pen="23428960733", dob="03/02/2022", admission=admission, environment="MOCK",
            )
            assert first_id == second_id  # same case, never a new one
        finally:
            browser.close()

    case = find_open_request_case(
        db_conn, student_id=student.student_id,
        case_type="RELEASE_REQUEST_SENT", portal="NATIONAL_UDISE",
    )
    assert case is not None
    assert case.request_case_id == first_id
