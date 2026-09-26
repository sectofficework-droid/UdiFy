"""Generic recovery wrapper for portal-automation failures (spec §13 /
TODO.md step 13: session expiry, timeout, unknown page/state, browser
crash, network failure — both portals).

None of these five scenarios was demonstrated by any source recording
(RULEBOOK.md's backlog rule, spec §AH: stay generic until new evidence
arrives) — so this deliberately never invents portal-specific detection
text (no fake "Session Expired" strings). Instead it classifies by the
KIND of failure Playwright itself reports and always captures a full
diagnostic (RULEBOOK §L2/§L3) before surfacing a structured, typed error
the caller can act on.
"""

from __future__ import annotations

import sqlite3
from typing import Callable, TypeVar

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.db.students import upsert_student
from src.db.workflow_runs import complete_run, start_run
from src.diagnostics.capture import capture_failure
from src.portals.base import AutomationPausedForUser, PortalError
from src.sheets.models import Student

T = TypeVar("T")


class RecoverableAutomationError(PortalError):
    """Playwright timed out waiting for an expected state — the generic
    signature shared by session expiry, timeout, and an unrecognized
    page/state (spec never confirms distinguishing text for any of
    these). The caller should stop this student's run and persist
    checkpoint state (spec §13: pause and resume from checkpoint, never
    blindly repeat the portal action) rather than retry automatically."""

    def __init__(self, diagnostic_id: str, *, retry_allowed: bool = True):
        super().__init__(f"Diagnostic ID: {diagnostic_id}")
        self.diagnostic_id = diagnostic_id
        self.retry_allowed = retry_allowed


class BrowserOrNetworkFailureError(PortalError):
    """The browser/page itself failed (crash, closed, network-level
    Playwright error) rather than the portal returning an unexpected
    state. Same recovery posture as RecoverableAutomationError."""

    def __init__(self, diagnostic_id: str):
        super().__init__(f"Diagnostic ID: {diagnostic_id}")
        self.diagnostic_id = diagnostic_id


def run_with_recovery(
    fn: Callable[[], T],
    *,
    conn: sqlite3.Connection,
    environment: str,
    workflow: str,
    run_id: str | None = None,
    student_id: str | None = None,
    student: Student | None = None,
) -> T:
    """Runs `fn` (a portal-adapter call or a small sequence of them).

    `AutomationPausedForUser` and any already-structured `PortalError`
    pass through unchanged — they're deliberate, meaningful signals this
    layer must not reclassify. A `PlaywrightTimeoutError` becomes
    `RecoverableAutomationError`; any other Playwright-level error
    becomes `BrowserOrNetworkFailureError`. Both are always preceded by a
    captured diagnostic.

    Also persists a `workflow_runs` row for this run_id (spec §13): started
    here, marked complete only if `fn` returns normally. Any exception path
    below leaves it incomplete — a crash is then a queryable DB fact, not
    just a log line, and `src.db.workflow_runs.find_incomplete_run_with_
    checkpoint_flag` lets a one-shot portal-creation branch detect it
    before retrying (see src/engine/branches.py's New UDISE/New PEN
    guards). `workflow_runs.student_id` has a hard foreign key onto
    `students` (DB-DESIGN.md §B.4), so when `student` is supplied this
    upserts it first — the New UDISE/New PEN branches never call
    `upsert_student` themselves the way the Import/Release branches do.
    """
    if student_id is None and student is not None:
        student_id = student.student_id
    if run_id is not None and student is not None:
        upsert_student(conn, student)
    if run_id is not None and student_id is not None:
        start_run(
            conn, run_id=run_id, student_id=student_id, condition=workflow,
            environment=environment, current_state="STARTED",
        )
    try:
        result = fn()
    except AutomationPausedForUser:
        raise
    except PortalError:
        raise
    except PlaywrightTimeoutError as exc:
        diagnostic_id = capture_failure(
            conn,
            summary=(
                "Portal did not reach the expected state in time "
                "(timeout, session expiry, or an unrecognized page/state)"
            ),
            environment=environment, severity="ERROR", retry_allowed=True,
            run_id=run_id, student_id=student_id, workflow=workflow,
            error_code="PORTAL_TIMEOUT_OR_UNKNOWN_STATE", error_message=str(exc),
        )
        raise RecoverableAutomationError(diagnostic_id) from exc
    except PlaywrightError as exc:
        diagnostic_id = capture_failure(
            conn,
            summary="Browser or network failure during portal automation",
            environment=environment, severity="ERROR", retry_allowed=True,
            run_id=run_id, student_id=student_id, workflow=workflow,
            error_code="BROWSER_OR_NETWORK_FAILURE", error_message=str(exc),
        )
        raise BrowserOrNetworkFailureError(diagnostic_id) from exc
    else:
        if run_id is not None:
            complete_run(conn, run_id=run_id)
        return result
