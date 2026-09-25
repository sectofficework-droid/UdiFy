"""Shared VALIDATE_STUDENT + state-logging helpers for every condition engine."""

from __future__ import annotations

import logging

from src.diagnostics.logging_setup import log_event
from src.engine.branches import StudentIdentityError
from src.sheets.models import Student


def validate_student(logger: logging.Logger, student: Student) -> None:
    """spec's VALIDATE_STUDENT state (§78) — minimum identity fields present
    before any consequential action (Final Authority §E multi-attribute
    identity requirement starts here)."""
    missing = [
        field_name
        for field_name, value in (("name", student.name), ("class_name", student.class_name))
        if not value
    ]
    if missing:
        log_event(
            logger, logging.ERROR, "student identity validation failed",
            student_id=student.student_id, missing_fields=missing,
        )
        raise StudentIdentityError(
            f"Student {student.student_id!r} missing required fields: {missing}"
        )


def log_state(logger: logging.Logger, run_id: str, student_id: str, state: str, **fields) -> None:
    log_event(
        logger, logging.INFO, f"state: {state}",
        run_id=run_id, student_id=student_id, state=state, **fields,
    )
