"""No-blind-duplicate-submission guard for the New UDISE / New PEN
initialization branches (spec acceptance criteria: "No blind duplicate
submissions"). Unlike the Import/Release branches (see
test_duplicate_request_protection.py), these two are one-shot portal-
creation actions ("ADD NEW STUDENT" / "Add New Student") with no prior
`request_cases` row to check — the guard here is workflow_runs-based
(spec §13's checkpoint/resume, src/db/workflow_runs.py).

Each test simulates an interruption by hand-writing a `workflow_runs` row
that's never marked complete, then calls the branch again for the same
student and proves it never blindly resubmits the one-shot creation
action.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.students import upsert_student
from src.db.workflow_runs import patch_checkpoint, start_run
from src.engine.branches import BranchError, run_pen_new_branch, run_udise_new_branch
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import INITIALIZATION_SUCCESS_TEXT, NationalUDISEPortalAdapter
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


def _udise_student(student_id: str) -> tuple[MockSheetsRepository, Student]:
    sheets = MockSheetsRepository()
    udise_row = SheetRowRef("UDISE_Entry_(State)", "PH2", 5)
    student = Student(
        student_id=student_id, name="Guard Test Student", class_name="LKG/KG1/PP2",
        father_name="Test Father", mother_name="Test Mother", surname="TestSurname",
        dob="02/01/2022", udise_row=udise_row,
    )
    sheets.seed_student(student)
    sheets.write_cell(udise_row, "Student Name", "Guard Test Student")
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
    sheets.write_cell(udise_row, "Birth Cert Reg No", "13/2022")
    sheets.write_cell(udise_row, "Mother Tongue", "Odia")
    return sheets, student


def _pen_student(student_id: str) -> tuple[MockSheetsRepository, Student]:
    sheets = MockSheetsRepository()
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 5)
    student = Student(
        student_id=student_id, name="Guard Test Student", class_name="LKG/KG1/PP2",
        pen_row=pen_row,
    )
    sheets.seed_student(student)
    sheets.write_cell(pen_row, "Name of Student as per Aadhar Card", "Guard Test Student")
    sheets.write_cell(pen_row, "Mother Tongue", "Odia")
    sheets.write_cell(pen_row, "Admission Number in Present School (GR No)", "P091")
    sheets.write_cell(pen_row, "Height (cm)", "105")
    sheets.write_cell(pen_row, "Weight (kg)", "45")
    return sheets, student


def test_udise_new_branch_resumes_using_checkpointed_uid_without_reclicking_add_new_student(
    db_conn,
):
    sheets, student = _udise_student("s-guard-udise-resume")
    upsert_student(db_conn, student)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{GUJARAT_FIXTURE.as_posix()}")
            gujarat = GujaratUDISEPortalAdapter(page, timeout_ms=3000)
            gujarat.login("24224100067", "not-a-real-password")

            # Simulate attempt #1 reaching "ADD NEW STUDENT" and obtaining a
            # UID, then crashing before the sheet write — same portal calls
            # run_udise_new_branch itself would make.
            from src.engine.field_mapping import udise_row_to_birth_details, udise_row_to_cts_details

            udise_row_values = sheets.get_row_values(student.udise_row)
            gujarat.open_student_new_entry()
            gujarat.submit_manual_birth_details(udise_row_to_birth_details(udise_row_values))
            gujarat.submit_cts_details(udise_row_to_cts_details(udise_row_values))
            first_uid = gujarat.read_generated_uid("Guard Test Student")

            start_run(
                db_conn, run_id="crashed-udise-run", student_id=student.student_id,
                condition="TEST_UDISE_NEW", environment="MOCK", current_state="STARTED",
            )
            patch_checkpoint(
                db_conn, run_id="crashed-udise-run",
                patch={"udise_new_entered": True, "udise_new_uid": first_uid},
            )
            # Deliberately never call complete_run — this run "crashed" here.

            assert page.locator(".student-row").count() == 1

            # Attempt #2: the branch itself, resuming.
            result_uid = run_udise_new_branch(
                gujarat, sheets, db_conn, student, run_id="resumed-udise-run",
            )

            assert result_uid == first_uid
            # No second "ADD NEW STUDENT" click happened — still exactly one row.
            assert page.locator(".student-row").count() == 1

            assert sheets.get_row_values(student.udise_row)["UDISE No"] == first_uid
            assert sheets.get_row_color(student.udise_row) == GREEN
        finally:
            browser.close()


def test_udise_new_branch_raises_when_prior_attempt_uid_unknown(db_conn):
    sheets, student = _udise_student("s-guard-udise-ambiguous")
    upsert_student(db_conn, student)

    start_run(
        db_conn, run_id="crashed-udise-run-2", student_id=student.student_id,
        condition="TEST_UDISE_NEW", environment="MOCK", current_state="STARTED",
    )
    # Crashed before a UID was ever obtained — whether "ADD NEW STUDENT"
    # reached the portal is unknown.
    patch_checkpoint(
        db_conn, run_id="crashed-udise-run-2", patch={"udise_new_entered": True},
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{GUJARAT_FIXTURE.as_posix()}")
            gujarat = GujaratUDISEPortalAdapter(page, timeout_ms=3000)
            gujarat.login("24224100067", "not-a-real-password")

            with pytest.raises(BranchError, match="[Mm]anual review"):
                run_udise_new_branch(gujarat, sheets, db_conn, student, run_id="resumed-udise-run-2")

            # Never touched the portal — no student row was ever created.
            assert page.locator(".student-row").count() == 0
        finally:
            browser.close()


def test_pen_new_branch_raises_on_prior_interrupted_attempt_never_reinitializes(db_conn):
    sheets, student = _pen_student("s-guard-pen-interrupted")
    upsert_student(db_conn, student)

    start_run(
        db_conn, run_id="crashed-pen-run", student_id=student.student_id,
        condition="TEST_PEN_NEW", environment="MOCK", current_state="STARTED",
    )
    patch_checkpoint(db_conn, run_id="crashed-pen-run", patch={"pen_new_entered": True})

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            with pytest.raises(BranchError, match="[Mm]anual review"):
                run_pen_new_branch(national, sheets, db_conn, student, run_id="resumed-pen-run")

            # "Add New Student" was never clicked a second time.
            assert not page.get_by_text(INITIALIZATION_SUCCESS_TEXT).is_visible()
        finally:
            browser.close()
