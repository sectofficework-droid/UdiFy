"""workflow_runs persistence (DB-DESIGN.md §B.4, spec §13's "pause and
resume from checkpoint, never blindly repeat the portal action").

Deliberately narrow in scope. This module makes a crash/interruption
produce a diagnosable, queryable "how far did this run get" record, and
lets a one-shot portal-creation action (New UDISE Entry's "ADD NEW
STUDENT", New PEN Entry's "Add New Student") detect that a previous
attempt for the same student was interrupted before re-issuing that
click. It does NOT attempt to auto-resume a portal session mid-
transaction beyond that — no recording confirms a "reopen an
in-progress entry" screen on either portal, so genuinely picking back up
mid-form stays a manual-review path (RULEBOOK §J14: don't invent
unconfirmed portal navigation) except for the one case where resuming
means nothing more than reusing an already-confirmed value (the UDISE
UID) with adapter methods that run unconditionally anyway.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    student_id: str
    condition: str
    environment: str
    current_state: str
    checkpoint: dict
    started_at: str
    updated_at: str
    completed_at: str | None


def _row_to_workflow_run(row: sqlite3.Row) -> WorkflowRun:
    return WorkflowRun(
        run_id=row["run_id"], student_id=row["student_id"], condition=row["condition"],
        environment=row["environment"], current_state=row["current_state"],
        checkpoint=json.loads(row["checkpoint_json"] or "{}"),
        started_at=row["started_at"], updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


def start_run(
    conn: sqlite3.Connection, *, run_id: str, student_id: str, condition: str,
    environment: str, current_state: str,
) -> None:
    now = _now()
    with conn:
        conn.execute(
            """
            INSERT INTO workflow_runs (
                run_id, student_id, condition, environment, current_state,
                checkpoint_json, started_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (run_id, student_id, condition, environment, current_state, "{}", now, now),
        )


def patch_checkpoint(
    conn: sqlite3.Connection, *, run_id: str, patch: dict, current_state: str | None = None,
) -> None:
    """Merges `patch` into the run's existing checkpoint_json (never
    overwrites keys another branch already recorded for the same run —
    Condition 1/2/4 run more than one branch per run_id)."""
    row = conn.execute(
        "SELECT checkpoint_json FROM workflow_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    existing = json.loads(row["checkpoint_json"] or "{}") if row else {}
    existing.update(patch)
    now = _now()
    with conn:
        if current_state is not None:
            conn.execute(
                "UPDATE workflow_runs SET checkpoint_json = ?, current_state = ?, "
                "updated_at = ? WHERE run_id = ?",
                (json.dumps(existing), current_state, now, run_id),
            )
        else:
            conn.execute(
                "UPDATE workflow_runs SET checkpoint_json = ?, updated_at = ? WHERE run_id = ?",
                (json.dumps(existing), now, run_id),
            )


def complete_run(conn: sqlite3.Connection, *, run_id: str) -> None:
    now = _now()
    with conn:
        conn.execute(
            "UPDATE workflow_runs SET completed_at = ?, updated_at = ? WHERE run_id = ?",
            (now, now, run_id),
        )


def find_incomplete_run_with_checkpoint_flag(
    conn: sqlite3.Connection, *, student_id: str, flag_key: str,
) -> WorkflowRun | None:
    """Most recent not-yet-completed run for this student whose checkpoint
    has `flag_key` set (truthy) — used by a one-shot portal-creation
    action to detect a prior interrupted attempt at the SAME creation
    step before deciding whether it's safe to proceed."""
    rows = conn.execute(
        "SELECT * FROM workflow_runs WHERE student_id = ? AND completed_at IS NULL "
        "ORDER BY started_at DESC",
        (student_id,),
    ).fetchall()
    for row in rows:
        run = _row_to_workflow_run(row)
        if run.checkpoint.get(flag_key):
            return run
    return None
