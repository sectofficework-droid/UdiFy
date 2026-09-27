"""Tests for spreadsheet-write recovery after a portal action succeeded.

The behaviour under test is the one that must never be wrong: when the
portal work is already banked and only the spreadsheet write failed, the
recovery retries the SHEET and never the PORTAL. A regression here would
mean creating a second real student record on a government portal.
"""

from __future__ import annotations

import pytest

from src.db.connection import connect
from src.db.schema import initialize_database
from src.engine.sheet_recovery import SheetWriteRecoveryFailedError, recover_sheet_write
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GREEN, MockSheetsRepository

ROW = SheetRowRef("UDISE_Entry_(State)", "PH1", 5)


@pytest.fixture()
def conn():
    connection = connect(":memory:")
    initialize_database(connection)
    yield connection
    connection.close()


@pytest.fixture()
def student():
    return Student(
        student_id="aadhar:111122223333",
        name="Recovery Test Student",
        class_name="SR.KG",
        udise_row=ROW,
        pen_row=ROW,
    )


# ---------------- the happy path ----------------


def test_recovery_writes_the_portal_result_to_the_sheet(conn, student):
    sheets = MockSheetsRepository()
    recover_sheet_write(
        sheets, conn, student=student, row_ref=ROW,
        cell_values={"UDISE No": "2422410006726200"},
    )
    assert sheets.verify_cell(ROW, "UDISE No", "2422410006726200")


def test_recovery_also_applies_the_row_colour(conn, student):
    sheets = MockSheetsRepository()
    recover_sheet_write(
        sheets, conn, student=student, row_ref=ROW,
        cell_values={"UDISE No": "2422410006726200"}, row_color=GREEN,
    )
    assert sheets.get_row_color(ROW) == GREEN


# ---------------- idempotency: a value that already landed is not rewritten ----


def test_recovery_does_not_rewrite_a_value_that_already_landed(conn, student):
    """The write may have succeeded before the error was raised. Recovery
    must recognise that from the sheet itself, not repeat the write."""
    sheets = MockSheetsRepository()
    sheets.write_cell(ROW, "UDISE No", "2422410006726200")
    writes_before = len(sheets.write_log)

    recover_sheet_write(
        sheets, conn, student=student, row_ref=ROW,
        cell_values={"UDISE No": "2422410006726200"},
    )
    assert len(sheets.write_log) == writes_before, "must not rewrite an already-correct cell"


# ---------------- a transient failure is retried ----------------


def test_recovery_retries_through_a_transient_write_failure(conn, student):
    sheets = MockSheetsRepository()
    sheets.simulate_write_failure(times=1)  # first attempt fails, then works

    recover_sheet_write(
        sheets, conn, student=student, row_ref=ROW,
        cell_values={"UDISE No": "2422410006726200"},
    )
    assert sheets.verify_cell(ROW, "UDISE No", "2422410006726200")


# ---------------- a persistent failure escalates, never hides ----------------


def test_persistent_failure_raises_for_manual_review(conn, student):
    sheets = MockSheetsRepository()
    sheets.simulate_write_failure(times=99)

    with pytest.raises(SheetWriteRecoveryFailedError) as exc:
        recover_sheet_write(
            sheets, conn, student=student, row_ref=ROW,
            cell_values={"UDISE No": "2422410006726200"},
        )
    message = str(exc.value)
    # The message must tell the operator what to do and, critically, what
    # NOT to do.
    assert "Do not re-run" in message
    assert "duplicate" in message.lower()


def test_persistent_failure_writes_an_audit_event(conn, student):
    """The incident must be reconstructible from the local DB alone."""
    from src.db.events import get_case_history

    sheets = MockSheetsRepository()
    sheets.simulate_write_failure(times=99)
    with pytest.raises(SheetWriteRecoveryFailedError):
        recover_sheet_write(
            sheets, conn, student=student, row_ref=ROW,
            cell_values={"UDISE No": "2422410006726200"},
        )

    history = get_case_history(conn, student.student_id)
    codes = [e["event_code"] for e in history]
    assert "PEN_SPREADSHEET_UPDATE_FAILED" in codes


def test_audit_event_explains_the_portal_side_is_already_done(conn, student):
    from src.db.events import get_case_history

    sheets = MockSheetsRepository()
    sheets.simulate_write_failure(times=99)
    with pytest.raises(SheetWriteRecoveryFailedError):
        recover_sheet_write(
            sheets, conn, student=student, row_ref=ROW,
            cell_values={"UDISE No": "2422410006726200"},
        )

    history = get_case_history(conn, student.student_id)
    failure = [e for e in history if e["event_code"] == "PEN_SPREADSHEET_UPDATE_FAILED"][0]
    note = (failure["resolution_note"] or "") + (failure["error_message"] or "")
    assert "portal" in note.lower()
    assert "do not re-run" in note.lower()


# ---------------- the structural guarantee ----------------


def test_recovery_cannot_drive_a_portal():
    """The guarantee is structural, not a convention: the public function
    takes no portal adapter, so there is no code path from it to a click."""
    import inspect

    params = inspect.signature(recover_sheet_write).parameters
    assert "adapter" not in params
    assert "gujarat" not in params
    assert "national" not in params
    assert "browser" not in params
    assert "page" not in params
