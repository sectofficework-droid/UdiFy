"""Verify-after-uncertain-save: re-check state instead of repeating an action.

The gap this closes (TODO.md testing matrix: "Save succeeded but
confirmation not seen -> verify state, don't repeat").

The scenario is narrow and genuinely awkward: a portal save was submitted,
the portal never showed the expected confirmation, and the app cannot tell
whether the save landed or not. The tempting response is to click Save
again. On a one-shot action that is how you create a duplicate record on a
government portal, so this module makes the *verification* the only
allowed next step.

The rule, stated once:

    **When an action's outcome is uncertain, re-read the state. Never
    re-issue the action.**

`verify_or_report` therefore takes a *probe* — a cheap, read-only callable
that reports what the portal now shows — and never a callable that can
mutate anything. An `UnverifiedActionError` is raised when the probe cannot
confirm, carrying a message that tells the operator what was attempted and
what to check, and the audit event records the attempt so a human can
resolve it from the local DB alone.

Deliberately not automated: deciding that an unconfirmed save *did* land
and silently marking it GREEN is exactly the failure mode the spec's
consequential-action verification rule exists to prevent (Final Authority
§J). When the probe cannot answer, a human decides.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Callable

from src.db.events import CaseStatus, EventCode, PenCaseEvent, Performer, append_event
from src.diagnostics.logging_setup import get_logger, log_event
from src.sheets.models import Student

_logger = get_logger("engine.verify_after_save")


class UnverifiedActionError(Exception):
    """A consequential action's outcome could not be confirmed.

    Carries the evidence needed to resolve it manually. Never means
    "the action failed" — it means "the app does not know", which is a
    different and safer thing to say.
    """


def verify_or_report(
    conn: sqlite3.Connection,
    *,
    student: Student,
    action_description: str,
    probe: Callable[[], bool],
    environment: str = "MOCK",
    workflow: str = "UNKNOWN",
    case_status: CaseStatus = CaseStatus.ACTION_REQUIRED,
    run_id: str = "",
    max_probes: int = 3,
) -> None:
    """Confirm a submitted action actually took effect, or escalate.

    `probe` must be read-only and should return True once the portal shows
    the expected post-action state. It is called up to `max_probes` times
    so a slow-to-refresh page is not misreported as a failure.

    On success: returns None, and the caller may proceed to record the
    result. On failure: raises `UnverifiedActionError` and appends an
    auditable event. In **neither** case is the action re-issued — that is
    the whole point, and it is why this function has no way to submit
    anything.
    """
    for attempt in range(1, max_probes + 1):
        try:
            confirmed = bool(probe())
        except Exception as exc:
            log_event(
                _logger, logging.WARNING,
                "verification probe raised - treating as unconfirmed",
                error_code="VERIFY_PROBE_ERROR", action=action_description,
                attempt=attempt, error=f"{type(exc).__name__}: {exc}",
            )
            confirmed = False
        if confirmed:
            log_event(
                _logger, logging.INFO, "consequential action verified by state re-read",
                action=action_description, student_id=student.student_id, attempt=attempt,
            )
            return
        log_event(
            _logger, logging.WARNING, "post-action state not yet confirmed",
            error_code="VERIFY_STATE_UNCONFIRMED", action=action_description,
            student_id=student.student_id, attempt=attempt,
        )

    # Still unconfirmed after every attempt.
    log_event(
        _logger, logging.ERROR,
        "consequential action could not be verified - manual review required, "
        "action NOT repeated",
        error_code="ACTION_UNVERIFIED", action=action_description,
        student_id=student.student_id, attempts=max_probes,
    )
    append_event(
        conn,
        PenCaseEvent(
            case_id=student.student_id,
            student_id=student.student_id,
            student_name=student.name,
            workflow=workflow,
            event_code=EventCode.PEN_VERIFICATION_RESULT,
            case_status_before=case_status,
            case_status_after=case_status,
            spreadsheet_status="UNVERIFIED",
            spreadsheet_color="UNCHANGED",
            performed_by=Performer.AUTOMATION,
            environment=environment,
            portal_status="UNCONFIRMED",
            action_description=action_description,
            error_code="ACTION_UNVERIFIED",
            error_message=(
                f"{action_description}: submitted, but the expected state could not be "
                f"confirmed after {max_probes} re-reads."
            ),
            resolution_note=(
                "The action was submitted once and deliberately NOT repeated. Check the "
                "portal for this student to establish whether it took effect, then record "
                "the outcome manually. Do not re-run the workflow without checking first."
            ),
            metadata={"run_id": run_id, "attempts": max_probes},
        ),
    )
    raise UnverifiedActionError(
        f"{student.student_id!r}: {action_description} was submitted but its result could "
        f"not be confirmed after {max_probes} checks. The action has NOT been repeated. "
        "Check the portal for this student before doing anything else — re-running could "
        "create a duplicate record."
    )


__all__ = ["verify_or_report", "UnverifiedActionError"]
