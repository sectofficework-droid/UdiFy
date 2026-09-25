"""Shared pen_case_events audit-trail recording for every condition engine.

Every condition ends its successful run with the same 3-event pattern —
OPENED -> VERIFYING -> RESOLVED (DB-DESIGN.md §B.2's allowed-transition
chain) — so this is centralized rather than re-implemented per engine.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from src.db.events import (
    CaseStatus,
    EventCode,
    PenCaseEvent,
    Performer,
    append_event,
    get_current_status,
)
from src.sheets.models import Student
from src.sheets.repository import GREEN


class CaseNotInManualReviewError(Exception):
    """record_manual_resolution() only makes sense on a case currently
    at MANUAL_REVIEW — the operator flow is View Details -> Mark Action
    Completed -> resolve (spec §N)."""


def record_completion_event(
    conn: sqlite3.Connection,
    student: Student,
    *,
    run_id: str,
    environment: str,
    workflow: str,
    resolution_note: str,
    uid: str | None = None,
    pen_value: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    opened = append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_ACTION_REQUIRED_OPENED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.ACTION_REQUIRED,
            spreadsheet_status="IN_PROGRESS",
            spreadsheet_color="UNCHANGED",
            performed_by=Performer.AUTOMATION,
            environment=environment,
            uid_udise=uid,
            pen=pen_value,
            occurred_at=now,
            metadata={"run_id": run_id},
        ),
    )
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_VERIFICATION_RESULT,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.VERIFYING,
            spreadsheet_status="VERIFIED",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            uid_udise=uid,
            pen=pen_value,
            previous_event_id=opened,
            metadata={"run_id": run_id},
        ),
    )
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_RESOLVED,
            case_status_before=CaseStatus.VERIFYING,
            case_status_after=CaseStatus.RESOLVED,
            spreadsheet_status="COMPLETE",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            uid_udise=uid,
            pen=pen_value,
            resolution_note=resolution_note,
            metadata={"run_id": run_id},
        ),
    )


def record_pending_event(
    conn: sqlite3.Connection,
    student: Student,
    *,
    run_id: str,
    environment: str,
    workflow: str,
    event_code: EventCode,
    portal_status: str | None = None,
) -> None:
    """For branches that end in a pending state (REQUEST SENT / IMPORT
    PENDING), not a resolved completion — spec: these are never marked
    RESOLVED merely because a request was submitted (Final Authority §J)."""
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=event_code,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.ACTION_REQUIRED,
            spreadsheet_status="PENDING",
            spreadsheet_color="LIGHT_ORANGE",
            performed_by=Performer.AUTOMATION,
            environment=environment,
            portal_status=portal_status,
            metadata={"run_id": run_id},
        ),
    )


def record_nd_reconciliation_found_event(
    conn: sqlite3.Connection,
    student: Student,
    *,
    run_id: str,
    environment: str,
    previous_pen: str,
    actual_pen: str,
) -> None:
    """spec §165/§260/§263: ND reconciliation is a later, separate
    operation on an already-RESOLVED case — RESOLVED only transitions to
    REOPENED (DB-DESIGN.md §B.2), and a reopen deliberately starts a NEW
    case_cycle_id, preserving the original cycle's history immutably."""
    new_cycle = str(uuid.uuid4())
    reopened_id = append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow="ND_RECONCILIATION",
            event_code=EventCode.PEN_CASE_REOPENED,
            case_status_before=CaseStatus.RESOLVED,
            case_status_after=CaseStatus.REOPENED,
            spreadsheet_status="ND_RECONCILIATION_IN_PROGRESS",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            pen=previous_pen,
            case_cycle_id=new_cycle,
            reopen_reason="ND reconciliation found an actual PEN; reopening to record the update",
            metadata={"run_id": run_id},
        ),
    )
    verifying_id = append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow="ND_RECONCILIATION",
            event_code=EventCode.PEN_REOPEN_VERIFICATION,
            case_status_before=CaseStatus.REOPENED,
            case_status_after=CaseStatus.VERIFYING,
            spreadsheet_status="VERIFIED",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            pen=actual_pen,
            case_cycle_id=new_cycle,
            previous_event_id=reopened_id,
            metadata={"run_id": run_id},
        ),
    )
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow="ND_RECONCILIATION",
            event_code=EventCode.PEN_RESOLVED,
            case_status_before=CaseStatus.VERIFYING,
            case_status_after=CaseStatus.RESOLVED,
            spreadsheet_status="COMPLETE",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            pen=actual_pen,
            case_cycle_id=new_cycle,
            previous_event_id=verifying_id,
            resolution_note=f"ND reconciliation: PEN updated from {previous_pen!r} to {actual_pen!r}.",
            metadata={"run_id": run_id},
        ),
    )


def record_nd_reconciliation_ambiguous_event(
    conn: sqlite3.Connection,
    student: Student,
    *,
    run_id: str,
    environment: str,
    previous_pen: str,
) -> None:
    """spec §165.3: never silently pick a candidate — route to manual
    review instead. Opens a new cycle (see record_nd_reconciliation_found_
    event's docstring) ending at MANUAL_REVIEW, not RESOLVED."""
    new_cycle = str(uuid.uuid4())
    reopened_id = append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow="ND_RECONCILIATION",
            event_code=EventCode.PEN_CASE_REOPENED,
            case_status_before=CaseStatus.RESOLVED,
            case_status_after=CaseStatus.REOPENED,
            spreadsheet_status="ND_RECONCILIATION_IN_PROGRESS",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            pen=previous_pen,
            case_cycle_id=new_cycle,
            reopen_reason="ND reconciliation search returned ambiguous candidates",
            metadata={"run_id": run_id},
        ),
    )
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow="ND_RECONCILIATION",
            event_code=EventCode.PEN_STUDENT_MATCH_AMBIGUOUS,
            case_status_before=CaseStatus.REOPENED,
            case_status_after=CaseStatus.MANUAL_REVIEW,
            spreadsheet_status="MANUAL_REVIEW",
            spreadsheet_color=GREEN,
            performed_by=Performer.AUTOMATION,
            environment=environment,
            pen=previous_pen,
            case_cycle_id=new_cycle,
            previous_event_id=reopened_id,
            metadata={"run_id": run_id},
        ),
    )


def record_manual_resolution(
    conn: sqlite3.Connection,
    student: Student,
    *,
    run_id: str,
    environment: str,
    workflow: str,
    action_description: str,
    resolution_note: str,
    performed_by: Performer = Performer.MANUAL,
    uid: str | None = None,
    pen_value: str | None = None,
) -> None:
    """The resolve half of the manual-review flow (spec §N): `View
    Details` -> `Mark Action Completed` (requires an action description)
    -> resolve (requires a resolution note). Only valid on a case
    currently at MANUAL_REVIEW — continues that case's existing cycle
    (no new case_cycle_id), preserving the reopen/ambiguous-match history
    that put it there.
    """
    current = get_current_status(conn, student.student_id)
    if current is not CaseStatus.MANUAL_REVIEW:
        raise CaseNotInManualReviewError(
            f"{student.student_id!r} is at {current!r}, not MANUAL_REVIEW — "
            "record_manual_resolution() only applies to an open manual-review case"
        )

    completed_id = append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_MANUAL_ACTION_COMPLETED,
            case_status_before=CaseStatus.MANUAL_REVIEW,
            case_status_after=CaseStatus.MANUAL_REVIEW,
            spreadsheet_status="MANUAL_REVIEW",
            spreadsheet_color=GREEN,
            performed_by=performed_by,
            environment=environment,
            uid_udise=uid,
            pen=pen_value,
            action_description=action_description,
            metadata={"run_id": run_id},
        ),
    )
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_RESOLVED,
            case_status_before=CaseStatus.MANUAL_REVIEW,
            case_status_after=CaseStatus.RESOLVED,
            spreadsheet_status="COMPLETE",
            spreadsheet_color=GREEN,
            performed_by=performed_by,
            environment=environment,
            uid_udise=uid,
            pen=pen_value,
            resolution_note=resolution_note,
            previous_event_id=completed_id,
            metadata={"run_id": run_id},
        ),
    )
