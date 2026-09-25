"""End-to-end PEN Request Sent + View Sent Request test (DB-DESIGN.md
§C.3b/§C.3c), against the National UDISE+ fixture."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.engine.release_request import (
    StudentIdentityMismatchError,
    check_sent_request_status,
    generate_pen_release_request,
)
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter, ReleaseAdmissionDetail
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import LIGHT_ORANGE, MockSheetsRepository

NATIONAL_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "udise_plus" / "new_pen_entry.html"
)


@pytest.fixture()
def db_conn(tmp_path):
    conn = connect(tmp_path / "test.sqlite3")
    yield conn
    conn.close()


@pytest.fixture()
def national_page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
        adapter = NationalUDISEPortalAdapter(page, timeout_ms=3000)
        adapter.login("sunil.pradhan", "not-a-real-password")
        yield adapter
        browser.close()


def _student():
    pen_row = SheetRowRef(spreadsheet="PEN_Entry_(National)", tab="PH2", row_number=9)
    return Student(
        student_id="s-release-1",
        name="Test Release Student",
        class_name="LKG/KG1/PP2",
        pen_row=pen_row,
    )


def test_generate_release_request_and_check_sent_status(db_conn, national_page):
    sheets = MockSheetsRepository()
    student = _student()
    sheets.seed_student(student)

    request_case_id = generate_pen_release_request(
        national_page, sheets, db_conn, student,
        pen="23428960733", dob="03/02/2022",
        admission=ReleaseAdmissionDetail(
            class_name="LKG/KG1/PP2", section="A",
            admission_date="01/06/2026",
            remark="Please release the student from the school records",
        ),
        environment="MOCK",
    )
    assert request_case_id

    pen_values = sheets.get_row_values(student.pen_row)
    assert pen_values["REMARK"] == "REQUEST SENT"
    assert sheets.get_row_color(student.pen_row) == LIGHT_ORANGE

    check = check_sent_request_status(national_page, db_conn, request_case_id, environment="MOCK")
    assert check.normalized_status == "PENDING_AT_DESTINATION"
    assert check.classification == "STILL_PENDING"


def test_generate_release_request_rejects_identity_mismatch(db_conn, national_page):
    sheets = MockSheetsRepository()
    student = _student()
    student.name = "Someone Else Entirely"
    sheets.seed_student(student)

    with pytest.raises(StudentIdentityMismatchError):
        generate_pen_release_request(
            national_page, sheets, db_conn, student,
            pen="23428960733", dob="03/02/2022",
            admission=ReleaseAdmissionDetail(
                class_name="LKG/KG1/PP2", section="A",
                admission_date="01/06/2026",
                remark="Please release the student from the school records",
            ),
            environment="MOCK",
        )
