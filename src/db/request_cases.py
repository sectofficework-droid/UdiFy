"""request_cases persistence — DB-DESIGN.md §C.3d.

A student pending an outside action is never represented internally as
merely a spreadsheet color; `case_type`/`portal`/`request_type` keep
IMPORT PENDING and REQUEST SENT distinct even though both render LIGHT
ORANGE (spec "SHARED REQUEST-CASE MODEL AND DATABASE STATE
REQUIREMENTS").
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RequestCase:
    request_case_id: str
    student_id: str
    case_type: str  # IMPORT_PENDING_ACTIVE | RELEASE_REQUEST_SENT | TRANSFER_REQUEST_SENT
    portal: str  # NATIONAL_UDISE | GUJARAT_UDISE
    request_type: str  # NONE | RELEASE_REQUEST | TRANSFER_REQUEST
    request_no: str | None
    source_school_udise: str | None
    source_school_name: str | None
    source_school_state: str | None
    source_school_district: str | None
    source_school_block: str | None
    hos_name: str | None
    hos_contact: str | None
    raw_portal_status: str | None
    normalized_status: str | None
    environment: str
    created_at: str
    updated_at: str


def create_request_case(
    conn: sqlite3.Connection,
    *,
    student_id: str,
    case_type: str,
    portal: str,
    request_type: str,
    environment: str,
    request_no: str | None = None,
    source_school_udise: str | None = None,
    source_school_name: str | None = None,
    source_school_state: str | None = None,
    source_school_district: str | None = None,
    source_school_block: str | None = None,
    hos_name: str | None = None,
    hos_contact: str | None = None,
    raw_portal_status: str | None = None,
    normalized_status: str | None = None,
) -> str:
    request_case_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO request_cases (
                request_case_id, student_id, case_type, portal, request_type,
                request_no, source_school_udise, source_school_name,
                source_school_state, source_school_district, source_school_block,
                hos_name, hos_contact, raw_portal_status, normalized_status,
                environment, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                request_case_id, student_id, case_type, portal, request_type,
                request_no, source_school_udise, source_school_name,
                source_school_state, source_school_district, source_school_block,
                hos_name, hos_contact, raw_portal_status, normalized_status,
                environment, now, now,
            ),
        )
    return request_case_id


def update_request_case_status(
    conn: sqlite3.Connection,
    request_case_id: str,
    *,
    raw_portal_status: str,
    normalized_status: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            UPDATE request_cases
            SET raw_portal_status = ?, normalized_status = ?, updated_at = ?
            WHERE request_case_id = ?
            """,
            (raw_portal_status, normalized_status, now, request_case_id),
        )


def get_request_case(conn: sqlite3.Connection, request_case_id: str) -> RequestCase | None:
    row = conn.execute(
        "SELECT * FROM request_cases WHERE request_case_id = ?", (request_case_id,)
    ).fetchone()
    return RequestCase(**dict(row)) if row else None


def find_request_case_by_request_no(
    conn: sqlite3.Connection, request_no: str
) -> RequestCase | None:
    row = conn.execute(
        "SELECT * FROM request_cases WHERE request_no = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (request_no,),
    ).fetchone()
    return RequestCase(**dict(row)) if row else None


def find_open_request_case(
    conn: sqlite3.Connection, *, student_id: str, case_type: str, portal: str
) -> RequestCase | None:
    """Duplicate-submission protection (spec AI-operating-instructions
    #19: "Never duplicate a transfer request because a confirmation
    response was lost"). This table has no separate open/closed column —
    an existing row of a given (student, case_type, portal) already
    means that request/pending-import is still outstanding, since
    nothing here ever deletes or archives a row — so "does one exist" is
    exactly "is one already open." The caller checks this before
    submitting a new transfer/release/import request and skips
    resubmission if one is found.
    """
    row = conn.execute(
        "SELECT * FROM request_cases WHERE student_id = ? AND case_type = ? "
        "AND portal = ? ORDER BY created_at DESC LIMIT 1",
        (student_id, case_type, portal),
    ).fetchone()
    return RequestCase(**dict(row)) if row else None
