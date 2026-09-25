"""Condition 3 workflow engine: UDISE already imported (precondition) + New PEN.

Condition 3's "UDISE already available/imported" (spec §11/§149) means
UDISE is ALREADY resolved before this run starts — a precondition, not a
live action this run performs (see the architecture note in
UDIFY-SPECIFICATIONS.md this session resolved). This engine therefore
only verifies the precondition (UDISE row already GREEN) and then runs
the New PEN branch, shared with Condition 1.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass

from src.diagnostics.logging_setup import get_logger, log_event
from src.engine.audit import record_completion_event
from src.engine.branches import BranchError, run_pen_new_branch
from src.engine.resilience import run_with_recovery
from src.engine.routing import determine_id_track
from src.engine.validation import log_state, validate_student
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import GREEN, StudentSheetRepository

_logger = get_logger("engine.condition3")


class UdisePreconditionNotMetError(BranchError):
    """spec §33.9 Case 2: a UID existing is not enough — the row must
    already be GREEN, or this run must not assume UDISE is complete."""


@dataclass
class Condition3Result:
    student_id: str
    run_id: str
    uid: str
    pen_value: str
    final_state: str  # "COMPLETE"


class Condition3Engine:
    def __init__(
        self,
        sheets: StudentSheetRepository,
        national: NationalUDISEPortalAdapter,
        conn: sqlite3.Connection,
        environment: str,
    ):
        self.sheets = sheets
        self.national = national
        self.conn = conn
        self.environment = environment

    def _verify_udise_precondition(self, student: Student) -> str:
        if student.udise_row is None or not student.uid_udise:
            raise UdisePreconditionNotMetError(
                f"{student.student_id!r}: Condition 3 requires an already-known "
                "UDISE row and UID"
            )
        color = self.sheets.get_row_color(student.udise_row)
        if color != GREEN:
            log_event(
                _logger, logging.WARNING, "Condition 3 precondition not met: UDISE row is not GREEN",
                student_id=student.student_id, observed_color=color,
            )
            raise UdisePreconditionNotMetError(
                f"{student.student_id!r}: UDISE row is {color!r}, not GREEN — "
                "do not assume UDISE completion (spec §33.9 Case 2)"
            )
        return student.uid_udise

    def run(self, student: Student, *, section: str = "A") -> Condition3Result:
        run_id = str(uuid.uuid4())

        def _impl() -> Condition3Result:
            return self._run_impl(student, run_id, section=section)

        return run_with_recovery(
            _impl, conn=self.conn, environment=self.environment,
            workflow="CONDITION_3_UDISE_IMPORTED_NEW_PEN", run_id=run_id,
            student_id=student.student_id,
        )

    def _run_impl(self, student: Student, run_id: str, *, section: str) -> Condition3Result:
        log_state(_logger, run_id, student.student_id, "READ_SHEETS")
        validate_student(_logger, student)
        log_state(_logger, run_id, student.student_id, "VALIDATE_STUDENT")
        log_state(
            _logger, run_id, student.student_id, "DETERMINE_CLASS_ROUTE",
            id_track=determine_id_track(student.class_name).value,
        )
        log_state(_logger, run_id, student.student_id, "DETERMINE_ENTRY_CONDITION", condition=3)

        uid = self._verify_udise_precondition(student)
        log_state(_logger, run_id, student.student_id, "VERIFY_UDISE_PRECONDITION", uid=uid)

        pen_value = run_pen_new_branch(self.national, self.sheets, student, section=section)
        log_state(_logger, run_id, student.student_id, "VERIFY_PEN", pen=pen_value)

        log_state(_logger, run_id, student.student_id, "UPDATE_SHEETS")
        log_state(_logger, run_id, student.student_id, "LOG_SUCCESS")

        record_completion_event(
            self.conn, student, run_id=run_id, environment=self.environment,
            workflow="CONDITION_3_UDISE_IMPORTED_NEW_PEN", uid=uid, pen_value=pen_value,
            resolution_note=(
                f"Condition 3 completed: UDISE already GREEN ({uid}), PEN={pen_value} verified GREEN."
            ),
        )

        return Condition3Result(
            student_id=student.student_id, run_id=run_id, uid=uid,
            pen_value=pen_value, final_state="COMPLETE",
        )
