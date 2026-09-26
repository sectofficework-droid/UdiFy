"""Reusable per-branch workflow logic, shared across Condition 1-4 engines.

Extracted from the original Condition1Engine so Conditions 2-4 don't
duplicate the New UDISE / New PEN logic — they only differ in WHICH
branches run and in what combination (spec §11/§79/§149/§AA).
"""

from __future__ import annotations

import logging
import sqlite3

from src.db.request_cases import create_request_case, find_open_request_case
from src.db.students import upsert_student
from src.db.workflow_runs import find_incomplete_run_with_checkpoint_flag, patch_checkpoint
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
    gujarat: GujaratUDISEPortalAdapter, sheets: StudentSheetRepository,
    conn: sqlite3.Connection, student: Student, *, run_id: str,
) -> str:
    """New UDISE Entry (spec §13-32, §163, §W). Returns the generated UID.

    No blind duplicate submissions (spec acceptance criteria): "ADD NEW
    STUDENT" is a one-shot portal action, so before issuing it this checks
    for a previous interrupted attempt for the same student
    (`workflow_runs`, spec §13). If that attempt already obtained a UID,
    this resumes using it — `open_student_profile` onward runs
    unconditionally on every call anyway, so skipping straight to it isn't
    new/invented navigation, just reusing an already-confirmed value. If
    no UID was recorded, whether the portal-side click actually went
    through is unknown, so this refuses to guess and raises for manual
    review rather than risk creating a second student record.
    """
    if student.udise_row is None:
        raise StudentIdentityError(f"{student.student_id!r} has no UDISE sheet row")

    prior = find_incomplete_run_with_checkpoint_flag(
        conn, student_id=student.student_id, flag_key="udise_new_entered",
    )
    resumed_uid = prior.checkpoint.get("udise_new_uid") if prior else None
    if prior is not None and not resumed_uid:
        raise BranchError(
            f"{student.student_id!r}: a previous UDISE new-entry attempt "
            f"(run {prior.run_id}) was interrupted before a UID was "
            "confirmed — whether 'ADD NEW STUDENT' actually reached the "
            "Gujarat UDISE portal is unknown from here, and this will not "
            "resubmit blindly (spec: no blind duplicate submissions). "
            "Manual review required: check the portal directly for this "
            "student before retrying."
        )

    udise_row = sheets.get_row_values(student.udise_row)
    birth_details = udise_row_to_birth_details(udise_row)
    cts_details = udise_row_to_cts_details(udise_row)

    if resumed_uid:
        log_event(
            _logger, logging.INFO,
            "UDISE new-entry: resuming after interruption with the "
            "previously-obtained UID, not resubmitting ADD NEW STUDENT",
            student_id=student.student_id, uid=resumed_uid, prior_run_id=prior.run_id,
        )
        uid = resumed_uid
    else:
        patch_checkpoint(conn, run_id=run_id, patch={"udise_new_entered": True})
        gujarat.open_student_new_entry()
        gujarat.submit_manual_birth_details(birth_details)
        gujarat.submit_cts_details(cts_details)
        uid = gujarat.read_generated_uid(cts_details.student_name)
        patch_checkpoint(conn, run_id=run_id, patch={"udise_new_uid": uid})

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
    gujarat: GujaratUDISEPortalAdapter, sheets: StudentSheetRepository,
    conn: sqlite3.Connection, student: Student,
    *, class_name: str, environment: str,
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

    existing = find_open_request_case(
        conn, student_id=student.student_id,
        case_type="TRANSFER_REQUEST_SENT", portal="GUJARAT_UDISE",
    )
    if existing is not None:
        # spec AI-operating-instructions #19: never duplicate a transfer
        # request because a confirmation response was lost — a request
        # already on record for this student means one was already
        # submitted; resubmitting risks a second real transfer request.
        log_event(
            _logger, logging.INFO, "UDISE Import: request already sent, skipping resubmission",
            student_id=student.student_id, existing_request_case_id=existing.request_case_id,
        )
        return "REQUEST_SENT"

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

    upsert_student(conn, student)
    create_request_case(
        conn,
        student_id=student.student_id,
        case_type="TRANSFER_REQUEST_SENT",
        portal="GUJARAT_UDISE",
        request_type="TRANSFER_REQUEST",
        environment=environment,
        # Gujarat's Student Transfer Request List has no separate request
        # number (spec §X) — it's matched by UID, so the UID is stored in
        # this generic "portal identifier for the request" column instead.
        request_no=student.uid_udise,
    )

    log_event(
        _logger, logging.INFO, "UDISE Import transfer request submitted",
        student_id=student.student_id,
    )
    return "REQUEST_SENT"


# ============================== PEN branches ==============================
def run_pen_new_branch(
    national: NationalUDISEPortalAdapter, sheets: StudentSheetRepository,
    conn: sqlite3.Connection, student: Student, *, run_id: str, section: str = "A",
) -> str:
    """New PEN Entry (spec §34-53, §164, §Y). Returns "ND" on success —
    spec §54/§81/§128.3: ND + GREEN is a valid completed state.

    Raises AutomationPausedForUser if the Aadhaar consent dialog appears
    — this branch never clicks "I Agree" itself.

    No blind duplicate submissions: "Add New Student" is a one-shot
    portal action. Unlike the UDISE branch above, no recording confirms a
    way to reopen an in-progress National UDISE+ PEN entry, so a previous
    interrupted attempt for this student always raises for manual review
    here rather than resubmitting — this can only detect and block, not
    auto-resume (spec: no blind duplicate submissions; RULEBOOK §J14: no
    invented portal navigation).
    """
    if student.pen_row is None:
        raise StudentIdentityError(f"{student.student_id!r} has no PEN sheet row")

    prior = find_incomplete_run_with_checkpoint_flag(
        conn, student_id=student.student_id, flag_key="pen_new_entered",
    )
    if prior is not None:
        raise BranchError(
            f"{student.student_id!r}: a previous New PEN Entry attempt "
            f"(run {prior.run_id}) was interrupted after starting — whether "
            "'Add New Student' actually reached the National UDISE+ portal "
            "is unknown from here, and this adapter has no confirmed way to "
            "reopen an in-progress PEN entry, so it will not resubmit "
            "automatically (spec: no blind duplicate submissions). Manual "
            "review required: check the portal directly for this student "
            "before retrying."
        )

    pen_row = sheets.get_row_values(student.pen_row)
    init = pen_row_to_new_student_init(pen_row, class_name=student.class_name, section=section)

    patch_checkpoint(conn, run_id=run_id, patch={"pen_new_entered": True})
    national.initialize_new_student(init)
    patch_checkpoint(conn, run_id=run_id, patch={"pen_new_initialized": True})
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
    national: NationalUDISEPortalAdapter, sheets: StudentSheetRepository,
    conn: sqlite3.Connection, student: Student, *, environment: str,
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

    existing_case = find_open_request_case(
        conn, student_id=student.student_id,
        case_type="IMPORT_PENDING_ACTIVE", portal="NATIONAL_UDISE",
    )
    if existing_case is not None:
        log_event(
            _logger, logging.INFO, "PEN Import: already recorded as pending, skipping re-check",
            student_id=student.student_id, existing_request_case_id=existing_case.request_case_id,
        )
        return {
            "pen": None,
            "source_school_udise": existing_case.source_school_udise,
            "source_school_name": existing_case.source_school_name,
            "state": existing_case.source_school_state,
            "district": existing_case.source_school_district,
            "block": existing_case.source_school_block,
            "hos_name": existing_case.hos_name,
            "hos_contact": existing_case.hos_contact,
            "status": "ACTIVE",
        }

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

    upsert_student(conn, student)
    create_request_case(
        conn,
        student_id=student.student_id,
        case_type="IMPORT_PENDING_ACTIVE",
        portal="NATIONAL_UDISE",
        request_type="NONE",
        environment=environment,
        source_school_udise=track.source_school_udise,
        source_school_name=track.source_school_name,
        source_school_state=hos.state,
        source_school_district=hos.district,
        source_school_block=hos.block,
        hos_name=hos.hos_name,
        hos_contact=hos.hos_contact,
    )

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
