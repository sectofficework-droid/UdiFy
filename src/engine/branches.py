"""Reusable per-branch workflow logic, shared across Condition 1-4 engines.

Extracted from the original Condition1Engine so Conditions 2-4 don't
duplicate the New UDISE / New PEN logic — they only differ in WHICH
branches run and in what combination (spec §11/§79/§149/§AA).
"""

from __future__ import annotations

import logging

from src.diagnostics.logging_setup import get_logger, log_event
from src.engine.field_mapping import (
    pen_row_to_enrolment_profile_fields,
    pen_row_to_facility_profile_fields,
    pen_row_to_general_profile_fields,
    pen_row_to_new_student_init,
    udise_row_to_birth_details,
    udise_row_to_cts_details,
    udise_row_to_personal_tab_fields,
)
from src.portals.base import AutomationPausedForUser
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import GREEN, LIGHT_ORANGE, StudentSheetRepository

_logger = get_logger("engine.branches")


class BranchError(Exception):
    """Base class for branch-level failures."""


class SheetVerificationFailedError(BranchError):
    """spec Final Authority §J: never treat an unverified write as done."""


class StudentIdentityError(BranchError):
    pass


def write_and_verify(sheets: StudentSheetRepository, row_ref, column: str, value: str) -> None:
    sheets.write_cell(row_ref, column, value)
    if not sheets.verify_cell(row_ref, column, value):
        log_event(
            _logger, logging.ERROR, "spreadsheet write could not be verified",
            error_code="SHEETS_WRITE_UNVERIFIED", column=column,
        )
        raise SheetVerificationFailedError(f"Could not verify {column!r} = {value!r}")


# ============================= UDISE branches =============================
def run_udise_new_branch(
    gujarat: GujaratUDISEPortalAdapter, sheets: StudentSheetRepository, student: Student
) -> str:
    """New UDISE Entry (spec §13-32, §163, §W). Returns the generated UID."""
    if student.udise_row is None:
        raise StudentIdentityError(f"{student.student_id!r} has no UDISE sheet row")
    udise_row = sheets.get_row_values(student.udise_row)
    birth_details = udise_row_to_birth_details(udise_row)
    cts_details = udise_row_to_cts_details(udise_row)

    gujarat.open_student_new_entry()
    gujarat.submit_manual_birth_details(birth_details)
    gujarat.submit_cts_details(cts_details)
    uid = gujarat.read_generated_uid(cts_details.student_name)

    gujarat.open_student_profile(cts_details.student_name)
    gujarat.open_tab("Personal")
    gujarat.fill_tab(udise_row_to_personal_tab_fields(udise_row))
    gujarat.save_current_tab()

    write_and_verify(sheets, student.udise_row, "UDISE No", uid)
    sheets.set_row_color(student.udise_row, GREEN)
    if student.ogr_row is not None:
        write_and_verify(sheets, student.ogr_row, "UID", uid)

    log_event(
        _logger, logging.INFO, "UDISE new-entry branch verified complete",
        student_id=student.student_id, uid=uid,
    )
    return uid


def run_udise_import_branch(
    gujarat: GujaratUDISEPortalAdapter, sheets: StudentSheetRepository, student: Student,
    *, class_name: str,
) -> str:
    """UDISE Import / transfer-request (spec §X) — the confirmed ACTIVE/
    pending outcome only. The known UID (from OGR/TC, per spec §X's
    example — the operator already has it, the search doesn't discover
    it) is required as input; this branch never invents one.

    Returns "REQUEST_SENT". The successful/Dropbox outcome is NOT
    implemented — if the portal doesn't show the expected "other school"
    state, this raises rather than guessing (spec §300: ambiguous result
    -> manual review, never arbitrary classification).
    """
    if not student.uid_udise:
        raise StudentIdentityError(
            f"{student.student_id!r}: UDISE Import requires an already-known "
            "UID (e.g. from the student's Transfer Certificate) — none on record"
        )
    found = gujarat.search_existing_student_by_uid(class_name, student.uid_udise)
    if not found:
        log_event(
            _logger, logging.WARNING, "UDISE Import: search did not find the "
            "expected other-school student — ambiguous, not guessing an outcome",
            student_id=student.student_id, uid=student.uid_udise,
        )
        raise BranchError(
            f"UDISE Import search for UID {student.uid_udise!r} did not return "
            "the expected other-school match — manual review required "
            "(spec §300: never classify an ambiguous result)"
        )
    gujarat.confirm_transfer_request()

    if student.udise_row is not None:
        write_and_verify(sheets, student.udise_row, "REMARK", "REQUEST SENT")
        sheets.set_row_color(student.udise_row, LIGHT_ORANGE)

    log_event(
        _logger, logging.INFO, "UDISE Import transfer request submitted",
        student_id=student.student_id,
    )
    return "REQUEST_SENT"


# ============================== PEN branches ==============================
def run_pen_new_branch(
    national: NationalUDISEPortalAdapter, sheets: StudentSheetRepository, student: Student,
    *, section: str = "A",
) -> str:
    """New PEN Entry (spec §34-53, §164, §Y). Returns "ND" on success —
    spec §54/§81/§128.3: ND + GREEN is a valid completed state.

    Raises AutomationPausedForUser if the Aadhaar consent dialog appears
    — this branch never clicks "I Agree" itself.
    """
    if student.pen_row is None:
        raise StudentIdentityError(f"{student.student_id!r} has no PEN sheet row")
    pen_row = sheets.get_row_values(student.pen_row)
    init = pen_row_to_new_student_init(pen_row, class_name=student.class_name, section=section)

    national.initialize_new_student(init)
    national.go_to_fill_general_profile()
    national.fill_general_profile(pen_row_to_general_profile_fields(pen_row))
    national.proceed_from_general_profile()

    if national.check_aadhaar_consent_required():
        log_event(
            _logger, logging.INFO, "AUTOMATION_PAUSED_FOR_USER: Aadhaar consent",
            student_id=student.student_id,
        )
        raise AutomationPausedForUser(
            "Aadhaar demographic-authentication consent required",
            checkpoint=f"{student.student_id}:general_profile",
        )

    national.fill_enrolment_profile(pen_row_to_enrolment_profile_fields(pen_row))
    national.fill_facility_profile(pen_row_to_facility_profile_fields(pen_row))
    national.complete_profile_preview()

    pen_value = "ND"
    write_and_verify(sheets, student.pen_row, "PEN", pen_value)
    sheets.set_row_color(student.pen_row, GREEN)

    log_event(
        _logger, logging.INFO, "PEN new-entry branch verified complete",
        student_id=student.student_id, pen=pen_value,
    )
    return pen_value


def run_pen_import_branch(
    national: NationalUDISEPortalAdapter, sheets: StudentSheetRepository, student: Student,
) -> dict:
    """PEN Import — Other School ACTIVE (DB-DESIGN.md §C.3a, the newly-
    confirmed spec section). Only the confirmed ACTIVE/pending outcome —
    if Student Status isn't ACTIVE, this raises rather than guessing what
    that means (spec §296.1: do not classify without evidence for it).

    Returns a dict of the captured source-school/HOS info — the caller
    writes it to the IMPORT PENDING sheet tab (spec §16); this branch
    itself doesn't know that sheet's exact columns, per the layering used
    everywhere else in this project (portal adapters -> engine -> sheets).
    """
    if not student.aadhaar:
        raise StudentIdentityError(
            f"{student.student_id!r}: PEN Import requires the student's Aadhaar number"
        )
    existing = national.check_aadhaar_availability(student.aadhaar)
    if not existing:
        raise BranchError(
            f"{student.student_id!r}: Aadhaar availability check found no "
            "existing registration — this student is not actually a PEN "
            "Import case (spec §6: duplicate-Aadhaar is the routing signal)"
        )
    track = national.open_track_by_details()
    search = national.global_student_search_by_pen(track.student_pen)

    if search.student_status != "ACTIVE":
        log_event(
            _logger, logging.WARNING, "PEN Import: Student Status is not ACTIVE — "
            "not classifying as Other School ACTIVE without evidence",
            student_id=student.student_id, observed_status=search.student_status,
        )
        raise BranchError(
            f"{student.student_id!r}: PEN Import Student Status = "
            f"{search.student_status!r}, not ACTIVE — spec only confirms the "
            "ACTIVE/pending outcome; route to documented workflow or manual review"
        )
    hos = national.open_hos_details()

    if student.pen_row is not None:
        write_and_verify(sheets, student.pen_row, "REMARK", "IMPORT PENDING")
        sheets.set_row_color(student.pen_row, LIGHT_ORANGE)

    log_event(
        _logger, logging.INFO, "PEN Import IMPORT_PENDING_ACTIVE_OTHER_SCHOOL",
        student_id=student.student_id, pen=track.student_pen,
        source_school_udise=track.source_school_udise,
    )
    return {
        "pen": track.student_pen,
        "source_school_udise": track.source_school_udise,
        "source_school_name": track.source_school_name,
        "state": hos.state,
        "district": hos.district,
        "block": hos.block,
        "hos_name": hos.hos_name,
        "hos_contact": hos.hos_contact,
        "status": search.student_status,
    }
