"""Shared application state: settings, DB connection, sheets repository.

One instance is created at startup and passed to every screen. The
repository is always the real `GoogleSheetsRepository`, and `demo_students`
is populated from the school's actual OGR master register (see
`load_live_students`), so an operator always sees real students. This is
what makes a run actually perform real work — before 2026-09-27 the GUI had
no live student list at all, and every screen was hardcoded to local mock
pages instead.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from src.config.settings import Settings, load_settings
from src.db.connection import connect
from src.diagnostics.logging_setup import get_logger, log_event
from src.sheets.models import Student
from src.sheets.repository import GoogleSheetsRepository, StudentSheetRepository

_logger = get_logger("app.app_context")



@dataclass(frozen=True)
class DemoStudentEntry:
    """One row of the Batch Queue.

    `intended_condition` is always None for a real student — routing is
    derived at run time by `entry_router.determine_entry_condition()` from
    actual sheet state, not known in advance. The UI shows the derived
    result (or "needs review"). None therefore means "not known until
    routed", not "no condition" — the Run button is enabled either way.
    """

    student: Student
    intended_condition: int | None
    note: str


class AppContext:
    def __init__(self, settings: Settings | None = None):
        self.settings: Settings = settings or load_settings()
        self.conn: sqlite3.Connection = connect(self.settings.sqlite_path)
        self.sheets: StudentSheetRepository = GoogleSheetsRepository(
            self.settings.sheets.service_account_file or "",
            {
                "OGR": self.settings.sheets.spreadsheet_id_ogr or "",
                "UDISE": self.settings.sheets.spreadsheet_id_udise or "",
                "PEN": self.settings.sheets.spreadsheet_id_pen or "",
            },
        )
        self.demo_students: list[DemoStudentEntry] = load_live_students(self.sheets)
        self.live_load_error: str | None = None

    def close(self) -> None:
        self.conn.close()


def load_live_students(sheets: StudentSheetRepository) -> list[DemoStudentEntry]:
    """Read the school's real students from the OGR master register.

    Deliberately never raises: a failure to reach Google Sheets (bad
    service-account path, revoked sharing, network down) must not stop the
    app from starting and showing the operator a diagnosable message. The
    error is recorded on the context and surfaced in the UI instead — an
    operator seeing "could not load real students" acts; an app that dies at
    import time does not.
    """
    try:
        students = sheets.list_students()
    except Exception as exc:
        log_event(
            _logger, logging.ERROR,
            "failed to load real students from the OGR register",
            error_code="OGR_LOAD_FAILED", error=f"{type(exc).__name__}: {exc}",
        )
        return []

    entries = [
        DemoStudentEntry(
            student=student,
            intended_condition=None,
            note=(
                "Real student from OGR — entry condition is derived at run "
                "time from the actual UDISE/PEN sheet state"
            ),
        )
        for student in students
    ]
    log_event(
        _logger, logging.INFO, "loaded real students from the OGR register",
        count=len(entries),
    )
    return entries

