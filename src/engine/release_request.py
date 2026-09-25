"""PEN Request Sent — Student Release Request generation + View Sent
Request (DB-DESIGN.md §C.3b/§C.3c).

A follow-up action after PEN Import has identified a student already
enrolled at another school (spec's own "PEN REQUEST SENT vs UDISE REQUEST
SENT" section: same business concept as the Gujarat transfer request, but
a separate National-portal workflow) — not part of Conditions 1-4's own
state machines, triggered explicitly once an operator decides to request
release.
"""

from __future__ import annotations

import logging
import sqlite3

from src.db.approval_checks import ApprovalCheck, record_approval_check
from src.db.request_cases import (
    create_request_case,
    find_open_request_case,
    get_request_case,
    update_request_case_status,
)
from src.db.students import upsert_student
from src.diagnostics.logging_setup import get_logger, log_event
from src.engine.branches import BranchError, write_and_verify
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter, ReleaseAdmissionDetail
from src.sheets.models import Student
from src.sheets.repository import LIGHT_ORANGE, StudentSheetRepository

_logger = get_logger("engine.release_request")


class StudentIdentityMismatchError(BranchError):
    """spec Final Authority §E: verify identity before any consequential
    action — never generate a release request for the wrong student."""


def generate_pen_release_request(
    national: NationalUDISEPortalAdapter,
    sheets: StudentSheetRepository,
    conn: sqlite3.Connection,
    student: Student,
    *,
    pen: str,
    dob: str,
    admission: ReleaseAdmissionDetail,
    environment: str,
) -> str:
    """Spec steps 1-8: Get Details -> verify identity -> Admission Detail
    -> Generate -> Confirm -> capture Request No. -> REQUEST_SENT/LIGHT
    ORANGE. Returns the request_case_id — an existing open one if a
    release request was already generated for this student (spec AI-
    operating-instructions #19: never duplicate a request because a
    confirmation response was lost), the portal is never touched twice.
    """
    existing_case = find_open_request_case(
        conn, student_id=student.student_id,
        case_type="RELEASE_REQUEST_SENT", portal="NATIONAL_UDISE",
    )
    if existing_case is not None:
        log_event(
            _logger, logging.INFO,
            "Release request already generated, skipping resubmission",
            student_id=student.student_id, existing_request_case_id=existing_case.request_case_id,
        )
        return existing_case.request_case_id

    details = national.get_student_release_details(pen, dob)

    if details.student_name.strip().lower() != student.name.strip().lower():
        log_event(
            _logger, logging.ERROR, "release-request identity check failed",
            student_id=student.student_id, expected_name=student.name,
            portal_name=details.student_name,
        )
        raise StudentIdentityMismatchError(
            f"{student.student_id!r}: release-request candidate name "
            f"{details.student_name!r} does not match {student.name!r} — "
            "refusing to generate a release request"
        )

    national.submit_release_admission_detail(admission)
    request_no = national.generate_release_request()

    upsert_student(conn, student)
    request_case_id = create_request_case(
        conn,
        student_id=student.student_id,
        case_type="RELEASE_REQUEST_SENT",
        portal="NATIONAL_UDISE",
        request_type="RELEASE_REQUEST",
        environment=environment,
        request_no=request_no,
        source_school_udise=details.udise_code,
        source_school_name=details.school_name,
    )

    if student.pen_row is not None:
        write_and_verify(sheets, student.pen_row, "REMARK", "REQUEST SENT")
        sheets.set_row_color(student.pen_row, LIGHT_ORANGE)

    log_event(
        _logger, logging.INFO, "PEN release request generated and recorded",
        student_id=student.student_id, request_no=request_no,
        request_case_id=request_case_id,
    )
    return request_case_id


def check_sent_request_status(
    national: NationalUDISEPortalAdapter,
    conn: sqlite3.Connection,
    request_case_id: str,
    *,
    environment: str,
) -> ApprovalCheck:
    """Spec's batched approval-check flow (DB-DESIGN.md §C.3c): read the
    Sent Requests row, preserve the raw status, normalize it, and classify
    against the previously recorded status. Never executes the next
    consequential portal action automatically on STATUS_CHANGED — that
    stays a manual-review/operator decision (spec §M)."""
    case = get_request_case(conn, request_case_id)
    if case is None or not case.request_no:
        raise ValueError(f"No request_case with a captured Request No. for {request_case_id!r}")

    national.open_sent_requests()
    record = national.find_sent_request(case.request_no)

    check = record_approval_check(
        conn,
        request_case_id=request_case_id,
        raw_portal_status=record.raw_status,
        normalized_status=record.normalized_status,
        previous_normalized_status=case.normalized_status,
        environment=environment,
    )
    update_request_case_status(
        conn, request_case_id,
        raw_portal_status=record.raw_status,
        normalized_status=record.normalized_status,
    )
    log_event(
        _logger, logging.INFO, "sent-request status check recorded",
        request_case_id=request_case_id, classification=check.classification,
        normalized_status=record.normalized_status,
    )
    return check
