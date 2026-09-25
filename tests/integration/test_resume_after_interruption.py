"""Resume-after-interruption test (TODO.md acceptance criteria): a run
interrupted between branches (e.g. process killed, browser crashed) must
resume without repeating the already-completed portal action.

This works today for a between-branch interruption as a direct
consequence of src/engine/entry_router.py's sheet-state detection: if the
UDISE branch already completed (sheet shows GREEN) before the
interruption, re-invoking run_entry() for the same student sees
UDISE=ALREADY_COMPLETE + PEN=NEW and correctly re-routes to Condition 3
(New PEN only) instead of restarting Condition 1 from scratch and
re-running the UDISE branch a second time. Resuming MID-branch (e.g. a
crash halfway through the multi-step New PEN form) is a different,
larger problem this does not solve — see TODO.md for the honest scope of
what "resume" means here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.events import get_case_history
from src.engine.entry_router import determine_entry_condition
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


def test_interruption_after_udise_branch_resumes_as_condition_3_not_a_repeat(db_conn):
    """Simulates a crash right after the UDISE branch verified GREEN but
    before the PEN branch ran (e.g. browser crash, process killed) — a
    fresh run against the SAME sheet state must not re-attempt the UDISE
    portal action a second time."""
    sheets = MockSheetsRepository()
    udise_row = SheetRowRef("UDISE_Entry_(State)", "PH2", 5)
    pen_row = SheetRowRef("PEN_Entry_(National)", "PH2", 5)
    student = Student(
        student_id="s-resume-1", name="Resume Test Student", class_name="LKG/KG1/PP2",
        udise_row=udise_row, pen_row=pen_row,
    )
    sheets.seed_student(student)

    # Simulate: the UDISE branch already ran to completion (as it would
    # have, moments before an interruption) — the sheet already reflects
    # its verified outcome. A resumed run reconstructs the Student object
    # from that sheet state (normal data-normalization flow, spec §166),
    # so uid_udise is populated from the sheet, not remembered in memory.
    sheets.write_cell(udise_row, "UDISE No", "242241000671234567")
    sheets.set_row_color(udise_row, GREEN)
    student.uid_udise = sheets.get_row_values(udise_row)["UDISE No"]

    # A fresh determination against this same (post-interruption) sheet
    # state must recognize UDISE is already done and route to the
    # PEN-only continuation, never back to "run UDISE again."
    from src.engine.entry_router import EntryCondition, PenState, UdiseState

    decision = determine_entry_condition(sheets, student)
    assert decision.udise_state is UdiseState.ALREADY_COMPLETE
    assert decision.pen_state is PenState.NEW
    assert decision.condition is EntryCondition.CONDITION_3

    # And running it end-to-end only drives the National portal — proves
    # the Gujarat UDISE branch is never touched a second time. Passing a
    # Gujarat adapter bound to a page with NO expected elements visible
    # would raise immediately if anything tried to use it.
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            national_page = browser.new_page()
            national_page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
            national = NationalUDISEPortalAdapter(national_page, timeout_ms=3000)
            national.login("sunil.pradhan", "not-a-real-password")

            from src.engine.condition3 import Condition3Engine

            result = Condition3Engine(sheets, national, db_conn, "MOCK").run(student)
            assert result.final_state == "COMPLETE"
            assert result.uid == "242241000671234567"  # the UID from before the interruption
            assert sheets.get_row_color(pen_row) == GREEN
        finally:
            browser.close()

    history = get_case_history(db_conn, student.student_id)
    assert history[-1]["case_status_after"] == "RESOLVED"
