"""Approval/status-check batch flow across both portals (spec §M).

ONE operator confirmation checks every eligible REQUEST SENT/LIGHT ORANGE
case across BOTH portals — never a per-student confirmation, and never an
automatic next consequential action on a status change (that stays a
manual-review/operator decision).
"""

from __future__ import annotations

import sqlite3

from src.db.approval_checks import ApprovalCheck, record_approval_check
from src.db.request_cases import get_request_case, update_request_case_status
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter


def check_request_case_status(
    gujarat: GujaratUDISEPortalAdapter,
    national: NationalUDISEPortalAdapter,
    conn: sqlite3.Connection,
    request_case_id: str,
    *,
    environment: str,
) -> ApprovalCheck:
    """Dispatches to the correct portal's status-read by `request_cases.
    portal`, then records + classifies exactly like the single-portal
    check functions (DB-DESIGN.md §C.3c) — this is the shared entry point
    a batch run calls once per eligible case."""
    case = get_request_case(conn, request_case_id)
    if case is None or not case.request_no:
        raise ValueError(f"No request_case with a portal identifier for {request_case_id!r}")

    if case.portal == "NATIONAL_UDISE":
        national.open_sent_requests()
        record = national.find_sent_request(case.request_no)
        raw_status, normalized_status = record.raw_status, record.normalized_status
    elif case.portal == "GUJARAT_UDISE":
        gujarat.open_transfer_request_list()
        record = gujarat.find_transfer_request(case.request_no)
        raw_status, normalized_status = record.raw_status, record.normalized_status
    else:
        raise ValueError(f"Unknown portal {case.portal!r} for request_case {request_case_id!r}")

    check = record_approval_check(
        conn,
        request_case_id=request_case_id,
        raw_portal_status=raw_status,
        normalized_status=normalized_status,
        previous_normalized_status=case.normalized_status,
        environment=environment,
    )
    update_request_case_status(
        conn, request_case_id, raw_portal_status=raw_status, normalized_status=normalized_status,
    )
    return check


def run_batch_status_check(
    gujarat: GujaratUDISEPortalAdapter,
    national: NationalUDISEPortalAdapter,
    conn: sqlite3.Connection,
    request_case_ids: list[str],
    *,
    environment: str,
) -> dict[str, ApprovalCheck]:
    """Represents the single operator-authorized batch confirmation (spec
    §M: "ONE confirmation, not per student") — the caller obtains that
    confirmation once, then passes every eligible case's id here. Returns
    every result; STATUS_CHANGED/UNKNOWN_PORTAL_STATUS entries are the
    caller's manual-review queue — this function never acts on them
    itself."""
    return {
        request_case_id: check_request_case_status(
            gujarat, national, conn, request_case_id, environment=environment,
        )
        for request_case_id in request_case_ids
    }
