"""Unit tests for src/engine/validation.py's VALIDATE_STUDENT state (spec
§78) — closes the "UDISE validation failure"/"PEN validation failure"
acceptance-criteria items: both conditions' engines call validate_student
before running either branch, so a missing identity field must block the
run before any portal action is attempted, for either side."""

from __future__ import annotations

import logging

import pytest

from src.engine.branches import StudentIdentityError
from src.engine.validation import validate_student
from src.sheets.models import Student

_logger = logging.getLogger("test")


def _student(**kwargs) -> Student:
    defaults = dict(student_id="s-validate-1", name="Valid Student", class_name="LKG/KG1/PP2")
    defaults.update(kwargs)
    return Student(**defaults)


def test_valid_student_passes():
    validate_student(_logger, _student())  # must not raise


def test_missing_name_raises_student_identity_error():
    with pytest.raises(StudentIdentityError, match="name"):
        validate_student(_logger, _student(name=""))


def test_missing_class_name_raises_student_identity_error():
    with pytest.raises(StudentIdentityError, match="class_name"):
        validate_student(_logger, _student(class_name=""))


def test_missing_both_name_and_class_name_reports_both_fields():
    with pytest.raises(StudentIdentityError) as excinfo:
        validate_student(_logger, _student(name="", class_name=""))
    assert "name" in str(excinfo.value)
    assert "class_name" in str(excinfo.value)


def test_missing_udise_row_blocks_udise_branch_before_any_portal_action():
    """The UDISE-side equivalent of a validation failure: run_udise_new_
    branch refuses to proceed at all without a UDISE sheet row, so no
    Gujarat portal action is ever attempted for a student who isn't
    actually eligible for that branch."""
    from src.engine.branches import run_udise_new_branch

    student = _student(udise_row=None)
    with pytest.raises(StudentIdentityError, match="UDISE"):
        run_udise_new_branch(gujarat=None, sheets=None, student=student)  # type: ignore[arg-type]


def test_missing_pen_row_blocks_pen_branch_before_any_portal_action():
    """The PEN-side equivalent: run_pen_new_branch refuses to proceed
    without a PEN sheet row, before any National portal action."""
    from src.engine.branches import run_pen_new_branch

    student = _student(pen_row=None)
    with pytest.raises(StudentIdentityError, match="PEN"):
        run_pen_new_branch(national=None, sheets=None, student=student)  # type: ignore[arg-type]
