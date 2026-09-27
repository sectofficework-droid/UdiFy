"""Recovery for a failed spreadsheet write after a portal action succeeded.

The gap this closes (TODO.md testing matrix: "Spreadsheet update failure
after portal success -> recovery path, never repeat the portal action").

The dangerous shape is specific and easy to get wrong: the portal work is
**already done** — a UID exists, a PEN was issued, a row is GREEN on the
government side — and then the app fails to write that result to the
spreadsheet. The naive recovery is to run the whole workflow again, which
re-issues a one-shot portal creation click and can create a *second* real
student record on a government portal. That is the single most damaging
thing this application could do, so recovery here is deliberately
one-directional: **retry the spreadsheet, never the portal.**

Three properties, each enforced rather than merely intended:

1. **The portal is never re-driven.** `recover_sheet_write` takes already-
   computed values and only touches the repository. It has no adapter
   argument and therefore cannot click anything.
2. **Every write is verified, and a verified value is never rewritten.**
   `verify_cell` is checked first, so a write that actually landed before
   the error is recognised as done instead of being repeated.
3. **A persistent failure escalates to manual review** with a diagnosable
   error, never a silent partial state.

Also here: the audit-trail event for such a failure, so the incident is
reconstructible from the local DB alone (RULEBOOK.md §L3).
"""

from __future__ import annotations

import logging
import sqlite3

from src.db.events import CaseStatus, EventCode, PenCaseEvent, Performer, append_event
from src.diagnostics.logging_setup import get_logger, log_event
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import StudentSheetRepository

_logger = get_logger("engine.sheet_recovery")


class SheetWriteRecoveryFailedError(Exception):
    """The spreadsheet still does not reflect a completed portal action.

    Raised instead of continuing, so the run stops with the portal work
    already banked and the sheet inconsistent — an explicitly recorded,
    operator-visible state rather than a silent one.
    """


def _row_ref_str(row_ref: SheetRowRef) -> str:
    return f"{row_ref.spreadsheet}/{row_ref.tab}/{row_ref.row_number}"


def _apply_one(
    sheets: StudentSheetRepository, row_ref: SheetRowRef, column: str, value: str
) -> bool:
    """Write and verify one cell, treating an already-correct cell as done.

    Returns True when the cell holds `value` afterwards. Idempotent by
    verification rather than by assumption: the sheet, not this function,
    is the source of truth about what it contains.
    """
    if sheets.verify_cell(row_ref, column, value):
        return True
    try:
        sheets.write_cell(row_ref, column, value)
    except Exception as exc:
        log_event(
            _logger, logging.WARNING, "spreadsheet write failed during recovery",
            error_code="SHEETS_WRITE_RETRY_FAILED", column=column,
            row_ref=_row_ref_str(row_ref), error=f"{type(exc).__name__}: {exc}",
        )
    return sheets.verify_cell(row_ref, column, value)


def recover_sheet_write(
    sheets: StudentSheetRepository,
    conn: sqlite3.Connection,
    *,
    student: Student,
    row_ref: SheetRowRef,
    cell_values: dict[str, str],
    row_color: str | None = None,
    run_id: str = "",
    environment: str = "MOCK",
    workflow: str = "NEW_UDISE",
    max_attempts: int = 3,
) -> None:
    """Make the spreadsheet reflect an already-completed portal action.

    `cell_values` and `row_color` are the results the portal produced; this
    function only writes them to the sheet. It never receives a portal
    adapter, so it is structurally incapable of repeating the portal action.
    """
    pending = dict(cell_values)
    for attempt in range(1, max_attempts + 1):
        outstanding = {
            column: value
            for column, value in pending.items()
            if not sheets.verify_cell(row_ref, column, value)
        }
        colour_pending = (
            row_color is not None and sheets.get_row_color(row_ref) != row_color
        )
        if not outstanding and not colour_pending:
            log_event(
                _logger, logging.INFO,
                "spreadsheet recovery completed (portal action not repeated)",
                row_ref=_row_ref_str(row_ref), attempt=attempt,
                columns=sorted(pending), row_color=row_color,
            )
            return

        log_event(
            _logger, logging.WARNING, "spreadsheet recovery attempt",
            error_code="SHEETS_WRITE_RECOVERY_ATTEMPT", attempt=attempt,
            row_ref=_row_ref_str(row_ref), outstanding=sorted(outstanding),
            colour_pending=colour_pending,
        )
        for column, value in outstanding.items():
            _apply_one(sheets, row_ref, column, value)
        if colour_pending and row_color is not None:
            try:
                sheets.set_row_color(row_ref, row_color)
            except Exception as exc:
                log_event(
                    _logger, logging.WARNING, "row colour write failed during recovery",
                    error_code="SHEETS_WRITE_RETRY_FAILED", target_color=row_color,
                    row_ref=_row_ref_str(row_ref), error=f"{type(exc).__name__}: {exc}",
                )

    # Every attempt is exhausted: escalate loudly rather than leave the
    # register silently inconsistent with the government portal.
    still_bad = [
        column for column, value in pending.items()
        if not sheets.verify_cell(row_ref, column, value)
    ]
    if row_color is not None and sheets.get_row_color(row_ref) != row_color:
        still_bad.append(f"__color__={row_color}")

    log_event(
        _logger, logging.ERROR,
        "spreadsheet recovery exhausted - manual review required",
        error_code="SHEETS_WRITE_RECOVERY_FAILED",
        row_ref=_row_ref_str(row_ref), still_incorrect=sorted(still_bad),
    )
    # Recorded through the project's own typed event path, so the incident
    # is reconstructible from the local audit DB alone (RULEBOOK.md §L3).
    # Same status before and after: the portal outcome did not change, only
    # the spreadsheet's ability to record it.
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_SPREADSHEET_UPDATE_FAILED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.ACTION_REQUIRED,
            spreadsheet_status="WRITE_FAILED",
            spreadsheet_color=row_color or "UNCHANGED",
            performed_by=Performer.AUTOMATION,
            environment=environment,
            error_code="SHEETS_WRITE_RECOVERY_FAILED",
            error_message=f"still incorrect after {max_attempts} attempts: "
                          f"{', '.join(sorted(still_bad)) or 'row colour'}",
            resolution_note=(
                "Portal action completed but the spreadsheet could not be updated. "
                "The portal record exists; the sheet is what is behind. Needs manual "
                "correction - do NOT re-run the portal action, that risks a duplicate "
                "government record."
            ),
            metadata={"run_id": run_id, "row_ref": _row_ref_str(row_ref)},
        ),
    )
    raise SheetWriteRecoveryFailedError(
        f"{student.student_id!r}: portal action succeeded but the spreadsheet still does "
        f"not reflect it after {max_attempts} attempts "
        f"(row {_row_ref_str(row_ref)}, cells: {', '.join(sorted(still_bad)) or 'row colour'}). "
        "The government portal already has this student recorded — correct the "
        "sheet manually. Do not re-run the workflow, that would risk a duplicate "
        "portal record."
    )


__all__ = ["recover_sheet_write", "SheetWriteRecoveryFailedError"]

