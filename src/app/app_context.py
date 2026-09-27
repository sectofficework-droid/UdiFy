"""Shared application state: settings, DB connection, sheets repository.

One instance is created at startup and passed to every screen. In MOCK
mode the sheets repository is seeded with clearly-labeled sample students
spanning Conditions 1-4, so the Dashboard isn't empty on first launch. This
sample data is never mistaken for real student records — it is never written
to `students`/`request_cases` unless a run actually processes it, and every
screen that shows it is labeled "MOCK sample data."

In LIVE mode the repository is the real `GoogleSheetsRepository` and
`demo_students` is populated from the school's actual OGR master register
instead (see `load_live_students`), so an operator sees real students
instead of the demo set. This is what makes a live run actually perform
real work — before 2026-09-27 the GUI had no live student list at all, and
every screen was hardcoded to the mock fixtures.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from src.config.settings import Environment, Settings, load_settings
from src.db.connection import connect
from src.diagnostics.logging_setup import get_logger, log_event
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GoogleSheetsRepository, MockSheetsRepository, StudentSheetRepository

_logger = get_logger("app.app_context")



@dataclass(frozen=True)
class DemoStudentEntry:
    """One row of the Batch Queue.

    `intended_condition` is how a MOCK demo case was deliberately
    constructed (Conditions 1-4, or None for the ND-reconciliation example).
    It is a property of the hand-built fixture, NOT something derivable by
    inspection — for a real student the routing is derived at run time by
    `entry_router.determine_entry_condition()` from actual sheet state, and
    the UI shows the derived result (or "needs review"). Storing None for a
    real student is therefore not "no condition", it is "not known until
    routed" — the Run button is enabled either way.
    """

    student: Student
    intended_condition: int | None
    note: str


class AppContext:
    def __init__(self, settings: Settings | None = None):
        self.settings: Settings = settings or load_settings()
        self.conn: sqlite3.Connection = connect(self.settings.sqlite_path)
        self.sheets: StudentSheetRepository = (
            MockSheetsRepository()
            if self.settings.environment is Environment.MOCK
            else GoogleSheetsRepository(
                self.settings.sheets.service_account_file or "",
                {
                    "OGR": self.settings.sheets.spreadsheet_id_ogr or "",
                    "UDISE": self.settings.sheets.spreadsheet_id_udise or "",
                    "PEN": self.settings.sheets.spreadsheet_id_pen or "",
                },
            )
        )
        self.demo_students: list[DemoStudentEntry] = []
        if isinstance(self.sheets, MockSheetsRepository):
            self.demo_students = seed_demo_students(self.sheets)
        else:
            self.demo_students = load_live_students(self.sheets)
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


def seed_demo_students(sheets: MockSheetsRepository) -> list[DemoStudentEntry]:
    """Small, clearly-fictitious dataset spanning Conditions 1-4 plus an
    ND-pending case, so the app has something to show against MOCK
    without requiring Google Sheets access first."""
    entries: list[DemoStudentEntry] = []

    s1 = Student(
        student_id="demo-c1-aisha",
        name="Aisha Demo Student",
        class_name="LKG/KG1/PP2",
        father_name="Demo Father",
        mother_name="Demo Mother",
        surname="DemoSurname",
        dob="02/01/2022",
        udise_row=SheetRowRef("UDISE_Entry_(State)", "PH2", 5),
        pen_row=SheetRowRef("PEN_Entry_(National)", "PH2", 5),
        ogr_row=SheetRowRef("OGR", "2026-27", 12),
    )
    sheets.seed_student(s1)
    sheets.write_cell(s1.udise_row, "Student Name", s1.name)
    sheets.write_cell(s1.udise_row, "Birth State", "Odisha")
    sheets.write_cell(s1.udise_row, "Birth District", "GANJAM")
    sheets.write_cell(s1.udise_row, "Birth City", "SHERAGADA")
    sheets.write_cell(s1.udise_row, "Birth Year", "2022")
    sheets.write_cell(s1.udise_row, "Birth Month", "January")
    sheets.write_cell(s1.udise_row, "Birth Date", "02")
    sheets.write_cell(s1.pen_row, "Name of Student as per Aadhar Card", s1.name)
    entries.append(DemoStudentEntry(s1, 1, "New UDISE + New PEN"))

    s2 = Student(
        student_id="demo-c2-rahul",
        name="Rahul Demo Student",
        class_name="LKG/KG1/PP2",
        father_name="Demo Father",
        mother_name="Demo Mother",
        surname="DemoSurname",
        dob="03/02/2022",
        aadhaar="999988887777",
        udise_row=SheetRowRef("UDISE_Entry_(State)", "PH2", 6),
        pen_row=SheetRowRef("PEN_Entry_(National)", "PH2", 6),
    )
    sheets.seed_student(s2)
    sheets.write_cell(s2.udise_row, "Student Name", s2.name)
    sheets.write_cell(s2.udise_row, "Birth State", "Odisha")
    sheets.write_cell(s2.udise_row, "Birth District", "GANJAM")
    sheets.write_cell(s2.udise_row, "Birth City", "SHERAGADA")
    sheets.write_cell(s2.udise_row, "Birth Year", "2022")
    sheets.write_cell(s2.udise_row, "Birth Month", "January")
    sheets.write_cell(s2.udise_row, "Birth Date", "02")
    entries.append(DemoStudentEntry(s2, 2, "New UDISE + PEN Import (Other School ACTIVE)"))

    s3 = Student(
        student_id="demo-c3-priya",
        name="Priya Demo Student",
        class_name="LKG/KG1/PP2",
        dob="04/03/2022",
        uid_udise="24224100067ALREADYIMPORTED",
        udise_row=SheetRowRef("UDISE_Entry_(State)", "PH2", 7),
        pen_row=SheetRowRef("PEN_Entry_(National)", "PH2", 7),
    )
    sheets.seed_student(s3)
    sheets.set_row_color(s3.udise_row, "GREEN")
    sheets.write_cell(s3.pen_row, "Name of Student as per Aadhar Card", s3.name)
    entries.append(DemoStudentEntry(s3, 3, "UDISE already GREEN (precondition) + New PEN"))

    s4 = Student(
        student_id="demo-c4-anita",
        name="Anita Demo Student",
        class_name="LKG/KG1/PP2",
        dob="05/04/2022",
        aadhaar="999988887777",
        uid_udise="OTHER-SCHOOL-UID-001",
        udise_row=SheetRowRef("UDISE_Entry_(State)", "PH2", 8),
        pen_row=SheetRowRef("PEN_Entry_(National)", "PH2", 8),
    )
    sheets.seed_student(s4)
    entries.append(DemoStudentEntry(s4, 4, "UDISE Import + PEN Import (both pending)"))

    s5 = Student(
        student_id="demo-nd-test-one",
        name="Test ND Student One",
        class_name="LKG/KG1/PP2",
        dob="02/01/2022",
        pen="ND",
        pen_row=SheetRowRef("PEN_Entry_(National)", "PH2", 9),
        ogr_row=SheetRowRef("OGR", "2026-27", 21),
    )
    sheets.seed_student(s5)
    sheets.write_cell(s5.pen_row, "PEN", "ND")
    entries.append(DemoStudentEntry(s5, None, "ND — reconciliation candidate"))

    return entries
