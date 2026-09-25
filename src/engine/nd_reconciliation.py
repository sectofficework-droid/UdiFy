"""ND Reconciliation — separate, later operation (spec §165/§259-264).

Never an automatic continuation of the New PEN workflow — triggered
explicitly, on an already-RESOLVED case, to check whether a student whose
spreadsheet PEN is `ND` has since received an actual 11-digit PEN.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import uuid

from src.diagnostics.logging_setup import get_logger, log_event
from src.engine.audit import (
    record_nd_reconciliation_ambiguous_event,
    record_nd_reconciliation_found_event,
)
from src.engine.branches import write_and_verify
from src.portals.udise_plus.adapter import NdReconciliationCandidate, NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import GREEN, StudentSheetRepository

_logger = get_logger("engine.nd_reconciliation")

_ACTUAL_PEN_PATTERN = re.compile(r"^\d{11}$")

PEN_FOUND = "PEN_FOUND"
STILL_ND = "STILL_ND"
AMBIGUOUS_MANUAL_REVIEW = "AMBIGUOUS_MANUAL_REVIEW"


def is_actual_pen(raw_value: str) -> bool:
    """spec §262: "NA" and anything else non-numeric-11-digit stays ND —
    never invented, never copied from UID/UDISE/school code."""
    return bool(_ACTUAL_PEN_PATTERN.match(raw_value.strip()))


def match_nd_candidate(
    student: Student, candidates: list[NdReconciliationCandidate]
) -> NdReconciliationCandidate | None:
    """spec §165.3/§260: never silently pick the first result. Matches on
    name, narrowed by DOB when more than one name match exists; returns
    None (caller routes to manual review) if still ambiguous."""
    name_matches = [
        c for c in candidates if c.student_name.strip().lower() == student.name.strip().lower()
    ]
    if len(name_matches) == 1:
        return name_matches[0]
    if len(name_matches) > 1 and student.dob:
        dob_matches = [c for c in name_matches if c.dob == student.dob]
        if len(dob_matches) == 1:
            return dob_matches[0]
    return None


def run_nd_reconciliation(
    national: NationalUDISEPortalAdapter,
    sheets: StudentSheetRepository,
    conn: sqlite3.Connection,
    student: Student,
    *,
    class_name: str,
    environment: str,
) -> str:
    """Returns PEN_FOUND / STILL_ND / AMBIGUOUS_MANUAL_REVIEW. Only
    PEN_FOUND writes the spreadsheet (PEN sheet + OGR, spec §263) and
    records a RESOLVED reopen-cycle; the other two outcomes leave the
    spreadsheet untouched."""
    run_id = str(uuid.uuid4())
    previous_pen = student.pen or "ND"

    candidates = national.search_for_nd_reconciliation(class_name, student.name)
    match = match_nd_candidate(student, candidates)

    if match is None:
        log_event(
            _logger, logging.WARNING, "ND reconciliation ambiguous — routing to manual review",
            student_id=student.student_id, candidate_count=len(candidates),
        )
        record_nd_reconciliation_ambiguous_event(
            conn, student, run_id=run_id, environment=environment, previous_pen=previous_pen,
        )
        return AMBIGUOUS_MANUAL_REVIEW

    if not is_actual_pen(match.current_pen):
        log_event(
            _logger, logging.INFO, "ND reconciliation: no actual PEN yet, keeping ND",
            student_id=student.student_id, observed_value=match.current_pen,
        )
        return STILL_ND

    if student.pen_row is not None:
        write_and_verify(sheets, student.pen_row, "PEN", match.current_pen)
        sheets.set_row_color(student.pen_row, GREEN)
    if student.ogr_row is not None:
        write_and_verify(sheets, student.ogr_row, "PEN", match.current_pen)

    record_nd_reconciliation_found_event(
        conn, student, run_id=run_id, environment=environment,
        previous_pen=previous_pen, actual_pen=match.current_pen,
    )
    log_event(
        _logger, logging.INFO, "ND reconciliation: actual PEN found and recorded",
        student_id=student.student_id, actual_pen=match.current_pen,
    )
    return PEN_FOUND
