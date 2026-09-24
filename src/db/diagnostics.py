"""DAO for the `diagnostics` table (DB-DESIGN.md §B, RULEBOOK.md §L9 persistence)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def record_diagnostic(
    conn: sqlite3.Connection,
    *,
    diagnostic_id: str,
    severity: str,
    summary: str,
    environment: str,
    retry_allowed: bool,
    run_id: str | None = None,
    student_id: str | None = None,
    workflow: str | None = None,
    expected_state: str | None = None,
    observed_state: str | None = None,
    url: str | None = None,
    page_title: str | None = None,
    selector_attempts: list[str] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    screenshot_path: str | None = None,
) -> None:
    with conn:
        conn.execute(
            """
            INSERT INTO diagnostics (
                diagnostic_id, run_id, student_id, workflow, severity, summary,
                expected_state, observed_state, url, page_title,
                selector_attempts_json, error_code, error_message,
                screenshot_path, retry_allowed, environment, occurred_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                diagnostic_id, run_id, student_id, workflow, severity, summary,
                expected_state, observed_state, url, page_title,
                json.dumps(selector_attempts or []), error_code, error_message,
                screenshot_path, int(retry_allowed), environment,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_diagnostic(conn: sqlite3.Connection, diagnostic_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM diagnostics WHERE diagnostic_id = ?", (diagnostic_id,)
    ).fetchone()


def list_recent_diagnostics(
    conn: sqlite3.Connection, limit: int = 50
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM diagnostics ORDER BY occurred_at DESC LIMIT ?", (limit,)
    ).fetchall()
