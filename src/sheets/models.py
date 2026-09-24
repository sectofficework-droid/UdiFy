"""Normalized student data model.

Built from raw spreadsheet cells before any portal action — never pass
raw cells directly into portal automation (spec §5355, IMPL-SPEC.md
"Data normalization").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SheetRowRef:
    """Where a value came from, for traceability and targeted writes."""

    spreadsheet: str  # "OGR" | "UDISE_Entry_(State)" | "PEN_Entry_(National)"
    tab: str  # e.g. "PH2", "IMPORT PENDING"
    row_number: int


@dataclass
class Student:
    """One student, normalized from the three spreadsheets (spec §156-158).

    Fields are optional where the source sheet may not have them yet —
    e.g. a brand-new OGR-only entry has no udise_row / pen_row.
    """

    student_id: str
    name: str
    class_name: str
    father_name: str | None = None
    mother_name: str | None = None
    surname: str | None = None
    dob: str | None = None  # normalized DD/MM/YYYY per spec §106/§166
    phase: str | None = None  # "PH1" | "PH2" | "PH3"
    gr_no: str | None = None
    aadhaar: str | None = None
    uid_udise: str | None = None
    pen: str | None = None

    ogr_row: SheetRowRef | None = None
    udise_row: SheetRowRef | None = None
    pen_row: SheetRowRef | None = None

    udise_status: str | None = None  # e.g. "GREEN", "REQUEST SENT"
    pen_status: str | None = None
