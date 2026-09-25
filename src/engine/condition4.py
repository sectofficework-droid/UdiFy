"""Condition 4 workflow engine: UDISE Import + PEN Import (both pending).

Composes two independently-confirmed pending-outcome branches (spec §11:
Condition 4 is not itself directly video-demonstrated end-to-end — it is
the combination of the confirmed UDISE Import and PEN Import — Other
School ACTIVE workflows, each already covered by branches.py). Neither
branch resolves the case; both leave it ACTION_REQUIRED/pending, per
Final Authority §J (never mark complete on a submitted request alone).
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass

from src.db.events import EventCode
from src.diagnostics.logging_setup import get_logger
from src.engine.audit import record_pending_event
from src.engine.branches import run_pen_import_branch, run_udise_import_branch
from src.engine.routing import determine_id_track
from src.engine.validation import log_state, validate_student
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import StudentSheetRepository

_logger = get_logger("engine.condition4")


@dataclass
class Condition4Result:
    student_id: str
    run_id: str
    udise_import_status: str  # "REQUEST_SENT"
    pen_import_info: dict
    final_state: str  # "BOTH_PENDING"


class Condition4Engine:
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

    def run(self, student: Student, *, class_name: str | None = None) -> Condition4Result:
        run_id = str(uuid.uuid4())
        log_state(_logger, run_id, student.student_id, "READ_SHEETS")
        validate_student(_logger, student)
        log_state(_logger, run_id, student.student_id, "VALIDATE_STUDENT")
        log_state(
            _logger, run_id, student.student_id, "DETERMINE_CLASS_ROUTE",
            id_track=determine_id_track(student.class_name).value,
        )
        log_state(_logger, run_id, student.student_id, "DETERMINE_ENTRY_CONDITION", condition=4)

        udise_status = run_udise_import_branch(
            self.gujarat, self.sheets, self.conn, student,
            class_name=class_name or student.class_name, environment=self.environment,
        )
        log_state(_logger, run_id, student.student_id, "UDISE_IMPORT_PENDING", status=udise_status)

        record_pending_event(
            self.conn, student, run_id=run_id, environment=self.environment,
            workflow="CONDITION_4_UDISE_IMPORT_PEN_IMPORT",
            event_code=EventCode.UDISE_REQUEST_SENT_OTHER_SCHOOL,
            portal_status=udise_status,
        )

        pen_import_info = run_pen_import_branch(
            self.national, self.sheets, self.conn, student, environment=self.environment,
        )
        log_state(
            _logger, run_id, student.student_id, "PEN_IMPORT_PENDING",
            pen=pen_import_info.get("pen"), status=pen_import_info.get("status"),
        )

        record_pending_event(
            self.conn, student, run_id=run_id, environment=self.environment,
            workflow="CONDITION_4_UDISE_IMPORT_PEN_IMPORT",
            event_code=EventCode.IMPORT_PENDING_ACTIVE_OTHER_SCHOOL,
            portal_status=pen_import_info.get("status"),
        )

        return Condition4Result(
            student_id=student.student_id, run_id=run_id,
            udise_import_status=udise_status, pen_import_info=pen_import_info,
            final_state="BOTH_PENDING",
        )
