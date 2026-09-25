"""Manual review flow end-to-end (spec §N): open -> action -> resolve.

Reaching MANUAL_REVIEW is already tested elsewhere (ND reconciliation's
ambiguous-match case). This covers the other half — an operator marking
the action completed and resolving the case — closing the "Manual review
flow works end-to-end" acceptance-criteria item.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.audit import CaseNotInManualReviewError, record_manual_resolution
from src.engine.nd_reconciliation import AMBIGUOUS_MANUAL_REVIEW, run_nd_reconciliation
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import MockSheetsRepository

NATIONAL_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "udise_plus" / "new_pen_entry.html"
)


@pytest.fixture()
def db_conn(tmp_path):
    conn = connect(tmp_path / "test.sqlite3")
    yield conn
    conn.close()


def test_manual_review_open_action_resolve_end_to_end(db_conn):
    sheets = MockSheetsRepository()
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 10)
    student = Student(
        student_id="s-manual-review-1", name="Test ND Ambiguous", class_name="LKG/KG1/PP2",
        dob="09/09/2022", pen="ND", pen_row=pen_row,
    )
    sheets.seed_student(student)
    sheets.write_cell(pen_row, "PEN", "ND")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            outcome = run_nd_reconciliation(
                national, sheets, db_conn, student, class_name="LKG/KG1/PP2", environment="MOCK",
            )
        finally:
            browser.close()

    assert outcome == AMBIGUOUS_MANUAL_REVIEW
    history = get_case_history(db_conn, student.student_id)
    assert history[-1]["case_status_after"] == "MANUAL_REVIEW"

    # -- action: an operator investigates and confirms which candidate is
    # actually the right student, then resolves the case.
    record_manual_resolution(
        db_conn, student, run_id=str(uuid.uuid4()), environment="MOCK",
        workflow="ND_RECONCILIATION",
        action_description="Confirmed the correct candidate by cross-checking DOB with the OGR.",
        resolution_note="Matched to the correct student; PEN updated manually after confirmation.",
        pen_value="23613114903",
    )

    history = get_case_history(db_conn, student.student_id)
    assert [row["event_code"] for row in history[-2:]] == [
        "PEN_MANUAL_ACTION_COMPLETED",
        "PEN_RESOLVED",
    ]
    assert history[-1]["case_status_after"] == "RESOLVED"
    assert history[-1]["resolution_note"]
    assert history[-2]["action_description"]
    # Same cycle throughout — reopen/ambiguous history preserved, not orphaned.
    assert len({row["case_cycle_id"] for row in history[-3:]}) == 1


def test_manual_resolution_refuses_when_not_in_manual_review(db_conn):
    sheets = MockSheetsRepository()
    student = Student(student_id="s-manual-review-2", name="Fresh Student", class_name="1st")
    sheets.seed_student(student)

    with pytest.raises(CaseNotInManualReviewError):
        record_manual_resolution(
            db_conn, student, run_id=str(uuid.uuid4()), environment="MOCK",
            workflow="ND_RECONCILIATION",
            action_description="n/a", resolution_note="n/a",
        )
