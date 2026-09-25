"""End-to-end approval/status-check batch test across both portals
(spec §M) — one batch call checks a Gujarat transfer request and a
National release request together."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.request_cases import create_request_case
from src.db.students import upsert_student
from src.engine.approval_batch import run_batch_status_check
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student

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


def test_batch_status_check_across_both_portals(db_conn):
    gujarat_student = Student(
        student_id="s-batch-gujarat-1", name="Aarushi Batch Student", class_name="1",
    )
    national_student = Student(
        student_id="s-batch-national-1", name="National Batch Student", class_name="LKG/KG1/PP2",
    )
    upsert_student(db_conn, gujarat_student)
    upsert_student(db_conn, national_student)

    gujarat_case_id = create_request_case(
        db_conn, student_id=gujarat_student.student_id,
        case_type="TRANSFER_REQUEST_SENT", portal="GUJARAT_UDISE",
        request_type="TRANSFER_REQUEST", environment="MOCK",
        request_no="OTHER-SCHOOL-UID-001",
    )
    national_case_id = create_request_case(
        db_conn, student_id=national_student.student_id,
        case_type="RELEASE_REQUEST_SENT", portal="NATIONAL_UDISE",
        request_type="RELEASE_REQUEST", environment="MOCK",
        request_no="SR/GJ/GJ/305364710",
    )

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

            results = run_batch_status_check(
                gujarat, national, db_conn,
                [gujarat_case_id, national_case_id],
                environment="MOCK",
            )

            assert results[gujarat_case_id].normalized_status == "PENDING"
            assert results[gujarat_case_id].classification == "STILL_PENDING"

            assert results[national_case_id].normalized_status == "PENDING_AT_DESTINATION"
            assert results[national_case_id].classification == "STILL_PENDING"
        finally:
            browser.close()
