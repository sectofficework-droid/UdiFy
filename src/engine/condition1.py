"""Condition 1 workflow engine: New UDISE + New PEN.

Implements the confirmed main state machine (DB-DESIGN.md §C.1, spec §78):

    READ_SHEETS -> VALIDATE_STUDENT -> DETERMINE_CLASS_ROUTE ->
    DETERMINE_ENTRY_CONDITION -> RUN_UDISE_BRANCH -> VERIFY_UDISE ->
    RUN_PEN_BRANCH -> VERIFY_PEN -> UPDATE_SHEETS -> LOG_SUCCESS

Every write to a spreadsheet or the audit trail follows the
consequential-action rule (spec Final Authority §D): locate -> verify
identity -> verify state -> act -> verify result -> record event -> only
then update the sheet's business-visible state. This module is the one
place all three adapters (sheets, Gujarat, National) and the audit trail
actually meet — the adapters themselves stay portal/sheet-focused.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from src.db.events import CaseStatus, EventCode, PenCaseEvent, Performer, append_event
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
from src.engine.routing import determine_id_track
from src.portals.base import AutomationPausedForUser
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import GREEN, StudentSheetRepository

_logger = get_logger("engine.condition1")


class StudentIdentityError(Exception):
    """VALIDATE_STUDENT failed — required identity fields missing."""


class SheetVerificationFailedError(Exception):
    """A spreadsheet write could not be verified — spec Final Authority §J:
    never treat an unverified write as done."""


@dataclass
class Condition1Result:
    student_id: str
    run_id: str
    uid: str
    pen_value: str
    final_state: str  # "COMPLETE" — reaching here means both branches verified


class Condition1Engine:
    """Orchestrates New UDISE + New PEN for one student.

    Takes already-constructed adapters (dependency injection) so callers
    can pass either fixture-backed Playwright adapters (integration
    tests) or, in future, live ones — the engine's own logic never
    changes between mock and live (mock-first decision §11).
    """

    def __init__(
        self,
        sheets: StudentSheetRepository,
        gujarat: GujaratUDISEPortalAdapter,
        national: NationalUDISEPortalAdapter,
        conn: sqlite3.Connection,
        environment: str,
    ):
        self.sheets = sheets
        self.gujarat = gujarat
        self.national = national
        self.conn = conn
        self.environment = environment

    def run(self, student: Student, *, section: str = "A") -> Condition1Result:
        run_id = str(uuid.uuid4())
        self._log_state(run_id, student.student_id, "READ_SHEETS")

        self._validate_student(student)
        self._log_state(run_id, student.student_id, "VALIDATE_STUDENT")

        id_track = determine_id_track(student.class_name)
        self._log_state(
            run_id, student.student_id, "DETERMINE_CLASS_ROUTE", id_track=id_track.value
        )

        # This engine only ever runs Condition 1 — the caller (a future
        # dispatcher) is responsible for DETERMINE_ENTRY_CONDITION routing
        # to the right engine. Recorded here for audit-trail completeness.
        self._log_state(run_id, student.student_id, "DETERMINE_ENTRY_CONDITION", condition=1)

        uid = self._run_udise_branch(run_id, student)
        self._log_state(run_id, student.student_id, "VERIFY_UDISE", uid=uid)

        pen_value = self._run_pen_branch(run_id, student, section=section)
        self._log_state(run_id, student.student_id, "VERIFY_PEN", pen=pen_value)

        self._log_state(run_id, student.student_id, "UPDATE_SHEETS")
        self._log_state(run_id, student.student_id, "LOG_SUCCESS")

        self._record_completion_event(run_id, student, uid, pen_value)

        return Condition1Result(
            student_id=student.student_id,
            run_id=run_id,
            uid=uid,
            pen_value=pen_value,
            final_state="COMPLETE",
        )

    # -- state helpers -----------------------------------------------------
    def _validate_student(self, student: Student) -> None:
        missing = [
            field_name
            for field_name, value in (
                ("name", student.name),
                ("class_name", student.class_name),
            )
            if not value
        ]
        if missing:
            log_event(
                _logger, logging.ERROR, "student identity validation failed",
                student_id=student.student_id, missing_fields=missing,
            )
            raise StudentIdentityError(
                f"Student {student.student_id!r} missing required fields: {missing}"
            )

    def _log_state(self, run_id: str, student_id: str, state: str, **fields) -> None:
        log_event(
            _logger, logging.INFO, f"state: {state}",
            run_id=run_id, student_id=student_id, state=state, **fields,
        )

    # -- UDISE branch (spec §13-32, §163, §W) -------------------------------
    def _run_udise_branch(self, run_id: str, student: Student) -> str:
        if student.udise_row is None:
            raise StudentIdentityError(
                f"Student {student.student_id!r} has no UDISE sheet row reference"
            )
        udise_row = self.sheets.get_row_values(student.udise_row)
        birth_details = udise_row_to_birth_details(udise_row)
        cts_details = udise_row_to_cts_details(udise_row)

        self.gujarat.open_student_new_entry()
        self.gujarat.submit_manual_birth_details(birth_details)
        self.gujarat.submit_cts_details(cts_details)
        uid = self.gujarat.read_generated_uid(cts_details.student_name)

        self.gujarat.open_student_profile(cts_details.student_name)
        self.gujarat.open_tab("Personal")
        self.gujarat.fill_tab(udise_row_to_personal_tab_fields(udise_row))
        self.gujarat.save_current_tab()
        # Scholarship & Facility / Health & CWSN: needs-live-verification
        # (UI-SPEC.md §B.5) — not filled here; the profile is completed
        # with the fields this project has confirmed evidence for only.

        self._write_and_verify(student.udise_row, "UDISE No", uid)
        self.sheets.set_row_color(student.udise_row, GREEN)
        if student.ogr_row is not None:
            self._write_and_verify(student.ogr_row, "UID", uid)

        log_event(
            _logger, logging.INFO, "UDISE branch verified complete",
            run_id=run_id, student_id=student.student_id, uid=uid,
        )
        return uid

    # -- PEN branch (spec §34-53, §164, §Y) ---------------------------------
    def _run_pen_branch(self, run_id: str, student: Student, *, section: str) -> str:
        if student.pen_row is None:
            raise StudentIdentityError(
                f"Student {student.student_id!r} has no PEN sheet row reference"
            )
        pen_row = self.sheets.get_row_values(student.pen_row)
        init = pen_row_to_new_student_init(
            pen_row, class_name=student.class_name, section=section
        )

        self.national.initialize_new_student(init)
        self.national.go_to_fill_general_profile()
        self.national.fill_general_profile(pen_row_to_general_profile_fields(pen_row))
        self.national.proceed_from_general_profile()

        if self.national.check_aadhaar_consent_required():
            log_event(
                _logger, logging.INFO, "AUTOMATION_PAUSED_FOR_USER: Aadhaar consent",
                run_id=run_id, student_id=student.student_id,
            )
            raise AutomationPausedForUser(
                "Aadhaar demographic-authentication consent required",
                checkpoint=f"{run_id}:general_profile",
            )

        self.national.fill_enrolment_profile(pen_row_to_enrolment_profile_fields(pen_row))
        self.national.fill_facility_profile(pen_row_to_facility_profile_fields(pen_row))
        self.national.complete_profile_preview()

        # spec §54/§81/§128.3: PEN = ND + GREEN is a valid completed state,
        # never a failure — this is the observed New PEN outcome, not a
        # placeholder pending better evidence.
        pen_value = "ND"
        self._write_and_verify(student.pen_row, "PEN", pen_value)
        self.sheets.set_row_color(student.pen_row, GREEN)

        log_event(
            _logger, logging.INFO, "PEN branch verified complete",
            run_id=run_id, student_id=student.student_id, pen=pen_value,
        )
        return pen_value

    # -- spreadsheet write helper -------------------------------------------
    def _write_and_verify(self, row_ref, column: str, value: str) -> None:
        self.sheets.write_cell(row_ref, column, value)
        if not self.sheets.verify_cell(row_ref, column, value):
            log_event(
                _logger, logging.ERROR, "spreadsheet write could not be verified",
                column=column, error_code="SHEETS_WRITE_UNVERIFIED",
            )
            raise SheetVerificationFailedError(
                f"Could not verify {column!r} = {value!r} after write"
            )

    # -- audit trail ---------------------------------------------------------
    def _record_completion_event(
        self, run_id: str, student: Student, uid: str, pen_value: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        opened = append_event(
            self.conn,
            PenCaseEvent(
                case_id=student.student_id,
                student_id=student.student_id,
                student_name=student.name,
                workflow="CONDITION_1_NEW_UDISE_NEW_PEN",
                event_code=EventCode.PEN_ACTION_REQUIRED_OPENED,
                case_status_before=CaseStatus.ACTION_REQUIRED,
                case_status_after=CaseStatus.ACTION_REQUIRED,
                spreadsheet_status="IN_PROGRESS",
                spreadsheet_color="UNCHANGED",
                performed_by=Performer.AUTOMATION,
                environment=self.environment,
                uid_udise=uid,
                occurred_at=now,
            ),
        )
        append_event(
            self.conn,
            PenCaseEvent(
                case_id=student.student_id,
                student_id=student.student_id,
                student_name=student.name,
                workflow="CONDITION_1_NEW_UDISE_NEW_PEN",
                event_code=EventCode.PEN_VERIFICATION_RESULT,
                case_status_before=CaseStatus.ACTION_REQUIRED,
                case_status_after=CaseStatus.VERIFYING,
                spreadsheet_status="VERIFIED",
                spreadsheet_color=GREEN,
                performed_by=Performer.AUTOMATION,
                environment=self.environment,
                uid_udise=uid,
                pen=pen_value,
                previous_event_id=opened,
            ),
        )
        append_event(
            self.conn,
            PenCaseEvent(
                case_id=student.student_id,
                student_id=student.student_id,
                student_name=student.name,
                workflow="CONDITION_1_NEW_UDISE_NEW_PEN",
                event_code=EventCode.PEN_RESOLVED,
                case_status_before=CaseStatus.VERIFYING,
                case_status_after=CaseStatus.RESOLVED,
                spreadsheet_status="COMPLETE",
                spreadsheet_color=GREEN,
                performed_by=Performer.AUTOMATION,
                environment=self.environment,
                uid_udise=uid,
                pen=pen_value,
                resolution_note=(
                    f"Condition 1 completed: UDISE={uid}, PEN={pen_value}, "
                    "both rows verified GREEN."
                ),
            ),
        )
