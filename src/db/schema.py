"""SQLite schema for UdiFy's local workflow/audit database.

This is NOT the OGR and never becomes the source of truth for student
identity (spec §AF). See governance/planning/DB-DESIGN.md §B for the
authoritative column-by-column spec this file implements.
"""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        version INTEGER NOT NULL
    )
    """,
    # -- students: normalized identity/reference (DB-DESIGN.md §B.4) -----
    """
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        father_name TEXT,
        mother_name TEXT,
        surname TEXT,
        dob TEXT,
        class_name TEXT NOT NULL,
        phase TEXT,
        gr_no TEXT,
        aadhaar_last4 TEXT,
        uid_udise TEXT,
        pen TEXT,
        ogr_row_ref TEXT,
        udise_row_ref TEXT,
        pen_row_ref TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    # -- workflow_runs: batch/run state, checkpoints (DB-DESIGN.md §B.4) -
    """
    CREATE TABLE IF NOT EXISTS workflow_runs (
        run_id TEXT PRIMARY KEY,
        student_id TEXT NOT NULL REFERENCES students(student_id),
        condition TEXT NOT NULL,
        environment TEXT NOT NULL CHECK (environment IN ('MOCK', 'LIVE')),
        current_state TEXT NOT NULL,
        checkpoint_json TEXT,
        started_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_workflow_runs_student
        ON workflow_runs(student_id)
    """,
    # -- pen_case_events: append-only, immutable (spec §P, DB-DESIGN §B.1)
    """
    CREATE TABLE IF NOT EXISTS pen_case_events (
        event_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        case_cycle_id TEXT NOT NULL,
        student_id TEXT NOT NULL,
        student_name TEXT NOT NULL,
        pen TEXT,
        uid_udise TEXT,
        workflow TEXT NOT NULL,
        event_code TEXT NOT NULL,
        event_version INTEGER NOT NULL CHECK (event_version > 0),
        previous_event_id TEXT,
        case_status_before TEXT NOT NULL,
        case_status_after TEXT NOT NULL,
        portal_status TEXT,
        portal_status_previous TEXT,
        spreadsheet_status TEXT NOT NULL,
        spreadsheet_color TEXT NOT NULL,
        action_description TEXT,
        resolution_note TEXT,
        reopen_reason TEXT,
        error_code TEXT,
        error_message TEXT,
        attempt_number INTEGER,
        authorized_by TEXT,
        performed_by TEXT NOT NULL CHECK (performed_by IN ('AUTOMATION', 'MANUAL')),
        environment TEXT NOT NULL CHECK (environment IN ('MOCK', 'LIVE')),
        occurred_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata_json TEXT,
        event_hash TEXT,
        previous_event_hash TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pen_case_events_case
        ON pen_case_events(case_id, case_cycle_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_pen_case_events_student
        ON pen_case_events(student_id)
    """,
    # -- portal_sessions: session/login state per portal (§112/§173) -----
    """
    CREATE TABLE IF NOT EXISTS portal_sessions (
        session_id TEXT PRIMARY KEY,
        portal TEXT NOT NULL CHECK (portal IN ('GUJARAT_UDISE', 'NATIONAL_UDISE')),
        environment TEXT NOT NULL CHECK (environment IN ('MOCK', 'LIVE')),
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        last_active_at TEXT NOT NULL,
        ended_at TEXT
    )
    """,
    # -- retry_log: attempt tracking (Final Authority §G, §88) -----------
    """
    CREATE TABLE IF NOT EXISTS retry_log (
        retry_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL REFERENCES workflow_runs(run_id),
        attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
        is_idempotent_retry INTEGER NOT NULL CHECK (is_idempotent_retry IN (0, 1)),
        reason TEXT NOT NULL,
        occurred_at TEXT NOT NULL
    )
    """,
    # -- diagnostics: screenshot/URL/DOM-state refs (Final Authority §H) -
    """
    CREATE TABLE IF NOT EXISTS diagnostics (
        diagnostic_id TEXT PRIMARY KEY,
        run_id TEXT REFERENCES workflow_runs(run_id),
        student_id TEXT,
        workflow TEXT,
        severity TEXT NOT NULL,
        summary TEXT NOT NULL,
        expected_state TEXT,
        observed_state TEXT,
        url TEXT,
        page_title TEXT,
        selector_attempts_json TEXT,
        error_code TEXT,
        error_message TEXT,
        screenshot_path TEXT,
        retry_allowed INTEGER NOT NULL CHECK (retry_allowed IN (0, 1)),
        environment TEXT NOT NULL CHECK (environment IN ('MOCK', 'LIVE')),
        occurred_at TEXT NOT NULL
    )
    """,
    # -- approval_checks: batched status-check runs (spec §M) ------------
    """
    CREATE TABLE IF NOT EXISTS approval_checks (
        check_id TEXT PRIMARY KEY,
        request_case_id TEXT NOT NULL,
        raw_portal_status TEXT NOT NULL,
        normalized_status TEXT NOT NULL,
        previous_normalized_status TEXT,
        classification TEXT NOT NULL CHECK (
            classification IN ('STILL_PENDING', 'STATUS_CHANGED', 'UNKNOWN_PORTAL_STATUS')
        ),
        environment TEXT NOT NULL CHECK (environment IN ('MOCK', 'LIVE')),
        checked_at TEXT NOT NULL,
        performed_by TEXT NOT NULL CHECK (performed_by IN ('AUTOMATION', 'MANUAL'))
    )
    """,
    # -- request_cases: do not collapse IMPORT PENDING vs REQUEST SENT ---
    # (DB-DESIGN.md §C.3d / master spec "SHARED REQUEST-CASE MODEL...")
    """
    CREATE TABLE IF NOT EXISTS request_cases (
        request_case_id TEXT PRIMARY KEY,
        student_id TEXT NOT NULL REFERENCES students(student_id),
        case_type TEXT NOT NULL CHECK (
            case_type IN ('IMPORT_PENDING_ACTIVE', 'RELEASE_REQUEST_SENT', 'TRANSFER_REQUEST_SENT')
        ),
        portal TEXT NOT NULL CHECK (portal IN ('NATIONAL_UDISE', 'GUJARAT_UDISE')),
        request_type TEXT NOT NULL CHECK (
            request_type IN ('NONE', 'RELEASE_REQUEST', 'TRANSFER_REQUEST')
        ),
        request_no TEXT,
        source_school_udise TEXT,
        source_school_name TEXT,
        source_school_state TEXT,
        source_school_district TEXT,
        source_school_block TEXT,
        hos_name TEXT,
        hos_contact TEXT,
        raw_portal_status TEXT,
        normalized_status TEXT,
        environment TEXT NOT NULL CHECK (environment IN ('MOCK', 'LIVE')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_request_cases_student
        ON request_cases(student_id)
    """,
]


def initialize_database(conn: sqlite3.Connection) -> None:
    """Create every table if missing, and record the schema version.

    Idempotent — safe to call on every application start.
    """
    conn.execute("PRAGMA foreign_keys = ON")
    with conn:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.execute(
            "INSERT INTO schema_meta (id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version = excluded.version",
            (SCHEMA_VERSION,),
        )
