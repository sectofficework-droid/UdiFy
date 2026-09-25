"""Condition 1 workflow engine: New UDISE + New PEN.

Implements the confirmed main state machine (DB-DESIGN.md §C.1, spec §78):

    READ_SHEETS -> VALIDATE_STUDENT -> DETERMINE_CLASS_ROUTE ->
    DETERMINE_ENTRY_CONDITION -> RUN_UDISE_BRANCH -> VERIFY_UDISE ->
    RUN_PEN_BRANCH -> VERIFY_PEN -> UPDATE_SHEETS -> LOG_SUCCESS

The UDISE/PEN branch logic itself lives in src/engine/branches.py, shared
with Conditions 2-4 — this module is just Condition 1's specific
combination (both branches, both "new") plus its audit-trail recording.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass

from src.engine.audit import record_completion_event
from src.engine.branches import (
    StudentIdentityError,
    run_pen_new_branch,
    run_udise_new_branch,
)
from src.engine.resilience import run_with_recovery
from src.engine.routing import determine_id_track
from src.engine.validation import validate_student, log_state
from src.diagnostics.logging_setup import get_logger
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import StudentSheetRepository

_logger = get_logger("engine.condition1")


@dataclass
class Condition1Result:
    student_id: str
    run_id: str
    uid: str
    pen_value: str
    final_state: str  # "COMPLETE" — reaching here means both branches verified


class Condition1Engine:
    """New UDISE + New PEN. Takes already-constructed adapters (dependency
    injection) — fixture-backed for tests, live ones later without any
    change to this class's own logic (mock-first decision §11)."""

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

        def _impl() -> Condition1Result:
            return self._run_impl(student, run_id, section=section)

        return run_with_recovery(
            _impl, conn=self.conn, environment=self.environment,
            workflow="CONDITION_1_NEW_UDISE_NEW_PEN", run_id=run_id,
            student_id=student.student_id,
        )

    def _run_impl(self, student: Student, run_id: str, *, section: str) -> Condition1Result:
        log_state(_logger, run_id, student.student_id, "READ_SHEETS")

        validate_student(_logger, student)
        log_state(_logger, run_id, student.student_id, "VALIDATE_STUDENT")

        id_track = determine_id_track(student.class_name)
        log_state(
            _logger, run_id, student.student_id, "DETERMINE_CLASS_ROUTE",
            id_track=id_track.value,
        )
        log_state(_logger, run_id, student.student_id, "DETERMINE_ENTRY_CONDITION", condition=1)

        uid = run_udise_new_branch(self.gujarat, self.sheets, student)
        log_state(_logger, run_id, student.student_id, "VERIFY_UDISE", uid=uid)

        pen_value = run_pen_new_branch(self.national, self.sheets, student, section=section)
        log_state(_logger, run_id, student.student_id, "VERIFY_PEN", pen=pen_value)

        log_state(_logger, run_id, student.student_id, "UPDATE_SHEETS")
        log_state(_logger, run_id, student.student_id, "LOG_SUCCESS")

        record_completion_event(
            self.conn, student, run_id=run_id, environment=self.environment,
            workflow="CONDITION_1_NEW_UDISE_NEW_PEN", uid=uid, pen_value=pen_value,
            resolution_note=(
                f"Condition 1 completed: UDISE={uid}, PEN={pen_value}, "
                "both rows verified GREEN."
            ),
        )

        return Condition1Result(
            student_id=student.student_id, run_id=run_id, uid=uid,
            pen_value=pen_value, final_state="COMPLETE",
        )
