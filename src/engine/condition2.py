"""Condition 2 workflow engine: New UDISE + PEN Import.

UDISE half identical to Condition 1 (New Entry, resolves to GREEN). PEN
half is the confirmed PEN Import — Other School ACTIVE workflow
(DB-DESIGN.md §C.3a), which resolves to IMPORT PENDING/LIGHT ORANGE, not
RESOLVED — spec: a pending import is never marked complete (Final
Authority §J).
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass

from src.db.events import EventCode
from src.diagnostics.logging_setup import get_logger
from src.engine.audit import record_pending_event
from src.engine.branches import run_pen_import_branch, run_udise_new_branch
from src.engine.routing import determine_id_track
from src.engine.validation import log_state, validate_student
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import StudentSheetRepository

_logger = get_logger("engine.condition2")


@dataclass
class Condition2Result:
    student_id: str
    run_id: str
    uid: str
    pen_import_info: dict
    final_state: str  # "UDISE_COMPLETE_PEN_PENDING"


class Condition2Engine:
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

    def run(self, student: Student) -> Condition2Result:
        run_id = str(uuid.uuid4())
        log_state(_logger, run_id, student.student_id, "READ_SHEETS")
        validate_student(_logger, student)
        log_state(_logger, run_id, student.student_id, "VALIDATE_STUDENT")
        log_state(
            _logger, run_id, student.student_id, "DETERMINE_CLASS_ROUTE",
            id_track=determine_id_track(student.class_name).value,
        )
        log_state(_logger, run_id, student.student_id, "DETERMINE_ENTRY_CONDITION", condition=2)

        uid = run_udise_new_branch(self.gujarat, self.sheets, student)
        log_state(_logger, run_id, student.student_id, "VERIFY_UDISE", uid=uid)

        pen_import_info = run_pen_import_branch(
            self.national, self.sheets, self.conn, student, environment=self.environment,
        )
        log_state(
            _logger, run_id, student.student_id, "PEN_IMPORT_PENDING",
            pen=pen_import_info.get("pen"), status=pen_import_info.get("status"),
        )

        record_pending_event(
            self.conn, student, run_id=run_id, environment=self.environment,
            workflow="CONDITION_2_NEW_UDISE_PEN_IMPORT",
            event_code=EventCode.IMPORT_PENDING_ACTIVE_OTHER_SCHOOL,
            portal_status=pen_import_info.get("status"),
        )

        return Condition2Result(
            student_id=student.student_id, run_id=run_id, uid=uid,
            pen_import_info=pen_import_info, final_state="UDISE_COMPLETE_PEN_PENDING",
        )
