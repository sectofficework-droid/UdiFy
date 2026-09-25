"""approval_checks persistence — batched status-check runs (spec §M).

One row per status-check performed against a request_case, whichever
portal it belongs to (Gujarat transfer requests or National release
requests share this table — DB-DESIGN.md's cross-cutting operations).
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ApprovalCheck:
    check_id: str
    request_case_id: str
    raw_portal_status: str
    normalized_status: str
    previous_normalized_status: str | None
    classification: str  # STILL_PENDING | STATUS_CHANGED | UNKNOWN_PORTAL_STATUS
    environment: str
    checked_at: str
    performed_by: str


def classify_status_check(
    normalized_status: str, previous_normalized_status: str | None
) -> str:
    """spec's batched approval-check classification (DB-DESIGN.md §C.3c):
    unchanged known status -> STILL_PENDING, changed -> STATUS_CHANGED
    (manual review), unrecognized wording -> UNKNOWN_PORTAL_STATUS
    (manual review) — never silently mapped."""
    if normalized_status == "UNKNOWN_PORTAL_STATUS":
        return "UNKNOWN_PORTAL_STATUS"
    if previous_normalized_status is not None and normalized_status != previous_normalized_status:
        return "STATUS_CHANGED"
    return "STILL_PENDING"


def record_approval_check(
    conn: sqlite3.Connection,
    *,
    request_case_id: str,
    raw_portal_status: str,
    normalized_status: str,
    previous_normalized_status: str | None,
    environment: str,
    performed_by: str = "AUTOMATION",
) -> ApprovalCheck:
    classification = classify_status_check(normalized_status, previous_normalized_status)
    check_id = str(uuid.uuid4())
    checked_at = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO approval_checks (
                check_id, request_case_id, raw_portal_status, normalized_status,
                previous_normalized_status, classification, environment,
                checked_at, performed_by
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                check_id, request_case_id, raw_portal_status, normalized_status,
                previous_normalized_status, classification, environment,
                checked_at, performed_by,
            ),
        )
    return ApprovalCheck(
        check_id=check_id,
        request_case_id=request_case_id,
        raw_portal_status=raw_portal_status,
        normalized_status=normalized_status,
        previous_normalized_status=previous_normalized_status,
        classification=classification,
        environment=environment,
        checked_at=checked_at,
        performed_by=performed_by,
    )


def get_latest_approval_check(
    conn: sqlite3.Connection, request_case_id: str
) -> ApprovalCheck | None:
    row = conn.execute(
        "SELECT * FROM approval_checks WHERE request_case_id = ? "
        "ORDER BY checked_at DESC LIMIT 1",
        (request_case_id,),
    ).fetchone()
    return ApprovalCheck(**dict(row)) if row else None
