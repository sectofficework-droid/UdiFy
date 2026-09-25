"""Shared application state: settings, DB connection, sheets repository.

One instance is created at startup and passed to every screen. In MOCK
mode (the only mode usable before the Live Verification Gate —
`GoogleSheetsRepository` raises `NotImplementedError` for every method
until then) the sheets repository is seeded with clearly-labeled sample
students spanning Conditions 1-4, so the Dashboard isn't empty on first
launch. This sample data is never mistaken for real student records — it
is never written to `students`/`request_cases` unless a run actually
processes it, and every screen that shows it is labeled "MOCK sample
data."
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from src.config.settings import Environment, Settings, load_settings
from src.db.connection import connect
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GoogleSheetsRepository, MockSheetsRepository, StudentSheetRepository


@dataclass(frozen=True)
class DemoStudentEntry:
    """One row of the MOCK-mode sample dataset. `intended_condition` is
    how this demo case was deliberately constructed (Conditions 1-4, or
    None for the ND-reconciliation example) — not a generic routing
    inference; a real Dashboard reading live sheet data would derive this
    from row state via the engine layer instead."""

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

    def close(self) -> None:
        self.conn.close()


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
