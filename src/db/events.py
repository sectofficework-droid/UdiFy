"""Append-only PEN case event log.

Implements DB-DESIGN.md §B.1-§B.3 (controlled statuses, event codes,
transitions) — see also the master spec §P/§Q/§R/§S. This module never
exposes an UPDATE or DELETE for pen_case_events: the table is append-only
by construction, not by convention.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.diagnostics.logging_setup import get_logger, log_event

_logger = get_logger("db.events")


class CaseStatus(str, Enum):
    ACTION_REQUIRED = "ACTION_REQUIRED"
    RETRYING = "RETRYING"
    VERIFYING = "VERIFYING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    RESOLVED = "RESOLVED"
    UNRESOLVED_CLOSED = "UNRESOLVED_CLOSED"
    REOPENED = "REOPENED"


class Performer(str, Enum):
    AUTOMATION = "AUTOMATION"
    MANUAL = "MANUAL"


class EventCode(str, Enum):
    PEN_ACTION_REQUIRED_OPENED = "PEN_ACTION_REQUIRED_OPENED"
    PEN_RETRY_STARTED = "PEN_RETRY_STARTED"
    PEN_RETRY_FAILED = "PEN_RETRY_FAILED"
    PEN_VERIFICATION_STARTED = "PEN_VERIFICATION_STARTED"
    PEN_VERIFICATION_RESULT = "PEN_VERIFICATION_RESULT"
    PEN_UNRESOLVED = "PEN_UNRESOLVED"
    PEN_MANUAL_ACTION_STARTED = "PEN_MANUAL_ACTION_STARTED"
    PEN_MANUAL_ACTION_COMPLETED = "PEN_MANUAL_ACTION_COMPLETED"
    PEN_RESOLUTION_STARTED = "PEN_RESOLUTION_STARTED"
    PEN_RESOLVED = "PEN_RESOLVED"
    PEN_SPREADSHEET_UPDATE_AUTHORIZED = "PEN_SPREADSHEET_UPDATE_AUTHORIZED"
    PEN_SPREADSHEET_UPDATE_COMPLETED = "PEN_SPREADSHEET_UPDATE_COMPLETED"
    PEN_SPREADSHEET_UPDATE_FAILED = "PEN_SPREADSHEET_UPDATE_FAILED"
    PEN_CASE_REOPENED = "PEN_CASE_REOPENED"
    PEN_REOPEN_VERIFICATION = "PEN_REOPEN_VERIFICATION"
    PEN_REOPENED_ACTION_REQUIRED = "PEN_REOPENED_ACTION_REQUIRED"
    PEN_UNRESOLVED_CLOSED = "PEN_UNRESOLVED_CLOSED"
    PEN_CASE_REOPENED_AFTER_UNRESOLVED = "PEN_CASE_REOPENED_AFTER_UNRESOLVED"
    PEN_INVALID_TRANSITION_ATTEMPT = "PEN_INVALID_TRANSITION_ATTEMPT"
    # PEN Import — Other School ACTIVE (DB-DESIGN.md §C.3a)
    EXISTING_STUDENT_FOUND_BY_AADHAAR = "EXISTING_STUDENT_FOUND_BY_AADHAAR"
    IMPORT_PENDING_ACTIVE_OTHER_SCHOOL = "IMPORT_PENDING_ACTIVE_OTHER_SCHOOL"
    PEN_AADHAAR_CHECK_FAILED = "PEN_AADHAAR_CHECK_FAILED"
    PEN_EXISTING_STUDENT_DETAILS_UNAVAILABLE = "PEN_EXISTING_STUDENT_DETAILS_UNAVAILABLE"
    PEN_STUDENT_MATCH_AMBIGUOUS = "PEN_STUDENT_MATCH_AMBIGUOUS"
    PEN_SEARCH_NO_RESULT = "PEN_SEARCH_NO_RESULT"
    # UDISE Import / transfer-request pending outcome (spec §X)
    UDISE_REQUEST_SENT_OTHER_SCHOOL = "UDISE_REQUEST_SENT_OTHER_SCHOOL"


# DB-DESIGN.md §B.2 — allowed transitions. Anything not listed here is
# rejected and logged as PEN_INVALID_TRANSITION_ATTEMPT.
_ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.ACTION_REQUIRED: {
        CaseStatus.RETRYING,
        CaseStatus.VERIFYING,
        CaseStatus.MANUAL_REVIEW,
    },
    CaseStatus.RETRYING: {CaseStatus.ACTION_REQUIRED, CaseStatus.VERIFYING},
    CaseStatus.VERIFYING: {
        CaseStatus.ACTION_REQUIRED,
        CaseStatus.MANUAL_REVIEW,
        CaseStatus.RESOLVED,
        CaseStatus.RETRYING,
    },
    CaseStatus.MANUAL_REVIEW: {
        CaseStatus.RESOLVED,
        CaseStatus.UNRESOLVED_CLOSED,
        CaseStatus.ACTION_REQUIRED,
    },
    CaseStatus.RESOLVED: {CaseStatus.REOPENED},
    CaseStatus.UNRESOLVED_CLOSED: {CaseStatus.REOPENED},
    CaseStatus.REOPENED: {
        CaseStatus.VERIFYING,
        CaseStatus.ACTION_REQUIRED,
        CaseStatus.MANUAL_REVIEW,
    },
}

# Events that mandate specific fields be populated (DB-DESIGN.md §B.1).
_REQUIRES_ACTION_DESCRIPTION = {EventCode.PEN_MANUAL_ACTION_COMPLETED}
_REQUIRES_RESOLUTION_NOTE = {EventCode.PEN_RESOLVED}
_REQUIRES_REOPEN_REASON = {
    EventCode.PEN_CASE_REOPENED,
    EventCode.PEN_CASE_REOPENED_AFTER_UNRESOLVED,
}
_REQUIRES_ERROR_FIELDS = {
    EventCode.PEN_RETRY_FAILED,
    EventCode.PEN_AADHAAR_CHECK_FAILED,
    EventCode.PEN_SPREADSHEET_UPDATE_FAILED,
}


class InvalidTransitionError(Exception):
    """Raised when a case-status transition is not in _ALLOWED_TRANSITIONS.

    The caller is expected to have already recorded a
    PEN_INVALID_TRANSITION_ATTEMPT event (see append_event) before this
    is raised — the event log captures the attempt even though it's
    rejected.
    """


class MissingRequiredFieldError(Exception):
    """Raised when an event code's mandatory field (spec §B.1) is absent."""


@dataclass(frozen=True)
class PenCaseEvent:
    case_id: str
    student_id: str
    student_name: str
    workflow: str
    event_code: EventCode
    case_status_before: CaseStatus
    case_status_after: CaseStatus
    spreadsheet_status: str
    spreadsheet_color: str
    performed_by: Performer
    environment: str  # "MOCK" | "LIVE" — see src.config.settings.Environment
    case_cycle_id: str | None = None
    pen: str | None = None
    uid_udise: str | None = None
    event_version: int = 1
    previous_event_id: str | None = None
    portal_status: str | None = None
    portal_status_previous: str | None = None
    action_description: str | None = None
    resolution_note: str | None = None
    reopen_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempt_number: int | None = None
    authorized_by: str | None = None
    occurred_at: str | None = None
    metadata: dict = field(default_factory=dict)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reject_missing_field(evt: PenCaseEvent, missing: str) -> None:
    log_event(
        _logger, logging.ERROR, "event rejected: missing required field",
        error_code="PEN_EVENT_MISSING_FIELD", event_code=evt.event_code.value,
        case_id=evt.case_id, missing_field=missing,
    )
    raise MissingRequiredFieldError(f"{evt.event_code} requires {missing}")


def _validate_required_fields(evt: PenCaseEvent) -> None:
    if evt.event_code in _REQUIRES_ACTION_DESCRIPTION and not evt.action_description:
        _reject_missing_field(evt, "action_description")
    if evt.event_code in _REQUIRES_RESOLUTION_NOTE and not evt.resolution_note:
        _reject_missing_field(evt, "resolution_note")
    if evt.event_code in _REQUIRES_REOPEN_REASON and not evt.reopen_reason:
        _reject_missing_field(evt, "reopen_reason")
    if evt.event_code in _REQUIRES_ERROR_FIELDS and not (
        evt.error_code and evt.error_message
    ):
        _reject_missing_field(evt, "error_code and error_message")


def _compute_hash(payload: dict, previous_event_hash: str | None) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    digest_input = (previous_event_hash or "") + canonical
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


def _current_cycle_id(conn: sqlite3.Connection, case_id: str) -> str | None:
    """The case_cycle_id of the most recent event for this case, if any.

    A caller that doesn't pass case_cycle_id explicitly should continue
    the case's existing cycle, not start a new random one on every call
    — a new cycle is only started deliberately, on reopen.
    """
    row = conn.execute(
        "SELECT case_cycle_id FROM pen_case_events WHERE case_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    return row["case_cycle_id"] if row else None


def _latest_event_hash(conn: sqlite3.Connection, case_id: str, case_cycle_id: str) -> str | None:
    row = conn.execute(
        "SELECT event_hash FROM pen_case_events "
        "WHERE case_id = ? AND case_cycle_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (case_id, case_cycle_id),
    ).fetchone()
    return row["event_hash"] if row else None


def append_event(conn: sqlite3.Connection, evt: PenCaseEvent) -> str:
    """Append one immutable event; returns the new event_id.

    Validates the case_status_before -> case_status_after transition
    against DB-DESIGN.md §B.2 before writing. An invalid transition is
    still recorded (as PEN_INVALID_TRANSITION_ATTEMPT, spec §R) and then
    rejected via InvalidTransitionError — the caller must not treat the
    rejected write as having changed the case's status.
    """
    _validate_required_fields(evt)

    same_status = evt.case_status_before == evt.case_status_after
    allowed = same_status or evt.case_status_after in _ALLOWED_TRANSITIONS.get(
        evt.case_status_before, set()
    )
    case_cycle_id = (
        evt.case_cycle_id
        or _current_cycle_id(conn, evt.case_id)
        or str(uuid.uuid4())
    )
    occurred_at = evt.occurred_at or _utcnow_iso()
    created_at = _utcnow_iso()
    event_code = evt.event_code

    if not allowed and evt.event_code is not EventCode.PEN_INVALID_TRANSITION_ATTEMPT:
        # Record the attempt itself before rejecting it, per spec §R.
        rejected_id = str(uuid.uuid4())
        previous_hash = _latest_event_hash(conn, evt.case_id, case_cycle_id)
        payload = {
            "event_id": rejected_id,
            "case_id": evt.case_id,
            "attempted_from": evt.case_status_before.value,
            "attempted_to": evt.case_status_after.value,
            "attempted_event_code": evt.event_code.value,
        }
        event_hash = _compute_hash(payload, previous_hash)
        with conn:
            conn.execute(
                """
                INSERT INTO pen_case_events (
                    event_id, case_id, case_cycle_id, student_id, student_name,
                    pen, uid_udise, workflow, event_code, event_version,
                    previous_event_id, case_status_before, case_status_after,
                    portal_status, portal_status_previous, spreadsheet_status,
                    spreadsheet_color, action_description, resolution_note,
                    reopen_reason, error_code, error_message, attempt_number,
                    authorized_by, performed_by, environment, occurred_at,
                    created_at, metadata_json, event_hash, previous_event_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rejected_id, evt.case_id, case_cycle_id, evt.student_id,
                    evt.student_name, evt.pen, evt.uid_udise, evt.workflow,
                    EventCode.PEN_INVALID_TRANSITION_ATTEMPT.value, evt.event_version,
                    evt.previous_event_id, evt.case_status_before.value,
                    evt.case_status_before.value,  # rejected: status does not change
                    evt.portal_status, evt.portal_status_previous,
                    evt.spreadsheet_status, evt.spreadsheet_color,
                    evt.action_description, evt.resolution_note, evt.reopen_reason,
                    evt.error_code, evt.error_message, evt.attempt_number,
                    evt.authorized_by, evt.performed_by.value, evt.environment,
                    occurred_at, created_at, json.dumps(evt.metadata), event_hash,
                    previous_hash,
                ),
            )
        log_event(
            _logger, logging.ERROR, "invalid case-status transition rejected",
            error_code="PEN_INVALID_TRANSITION_ATTEMPT", case_id=evt.case_id,
            attempted_from=evt.case_status_before.value,
            attempted_to=evt.case_status_after.value,
            attempted_event_code=event_code.value,
        )
        raise InvalidTransitionError(
            f"{evt.case_status_before} -> {evt.case_status_after} is not an "
            f"allowed transition (attempted via {event_code}); recorded as "
            f"{EventCode.PEN_INVALID_TRANSITION_ATTEMPT}"
        )

    event_id = str(uuid.uuid4())
    previous_hash = _latest_event_hash(conn, evt.case_id, case_cycle_id)
    payload = {
        "event_id": event_id,
        "case_id": evt.case_id,
        "event_code": evt.event_code.value,
        "case_status_after": evt.case_status_after.value,
        "occurred_at": occurred_at,
    }
    event_hash = _compute_hash(payload, previous_hash)

    with conn:
        conn.execute(
            """
            INSERT INTO pen_case_events (
                event_id, case_id, case_cycle_id, student_id, student_name,
                pen, uid_udise, workflow, event_code, event_version,
                previous_event_id, case_status_before, case_status_after,
                portal_status, portal_status_previous, spreadsheet_status,
                spreadsheet_color, action_description, resolution_note,
                reopen_reason, error_code, error_message, attempt_number,
                authorized_by, performed_by, environment, occurred_at,
                created_at, metadata_json, event_hash, previous_event_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event_id, evt.case_id, case_cycle_id, evt.student_id,
                evt.student_name, evt.pen, evt.uid_udise, evt.workflow,
                evt.event_code.value, evt.event_version, evt.previous_event_id,
                evt.case_status_before.value, evt.case_status_after.value,
                evt.portal_status, evt.portal_status_previous,
                evt.spreadsheet_status, evt.spreadsheet_color,
                evt.action_description, evt.resolution_note, evt.reopen_reason,
                evt.error_code, evt.error_message, evt.attempt_number,
                evt.authorized_by, evt.performed_by.value, evt.environment,
                occurred_at, created_at, json.dumps(evt.metadata), event_hash,
                previous_hash,
            ),
        )
    return event_id


def get_case_history(conn: sqlite3.Connection, case_id: str) -> list[sqlite3.Row]:
    """Full, immutable history for a case across every cycle, oldest first."""
    return conn.execute(
        "SELECT * FROM pen_case_events WHERE case_id = ? "
        "ORDER BY created_at ASC, rowid ASC",
        (case_id,),
    ).fetchall()


def get_current_status(conn: sqlite3.Connection, case_id: str) -> CaseStatus | None:
    row = conn.execute(
        "SELECT case_status_after FROM pen_case_events WHERE case_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    return CaseStatus(row["case_status_after"]) if row else None
