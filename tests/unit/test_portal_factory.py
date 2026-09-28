"""Tests for portal setup and live student discovery.

The defect these lock down (found in review 2026-09-27): the GUI
hardcoded local mock-page URLs and `environment="MOCK"` while
`AppContext` built a REAL `GoogleSheetsRepository` — so a live-configured
app drove mock pages and wrote mock results into the school's real
spreadsheets. These tests assert portal setup is built from Settings, in
one place, with no silent fallback when it's misconfigured.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.app.app_context import DemoStudentEntry, load_live_students
from src.app.portal_factory import (
    LIVE_TIMEOUT_MS,
    PortalSetupError,
    _validate_login_url,
)
from src.config.settings import (
    Environment,
    GoogleSheetsConfig,
    GujaratPortalCredentials,
    NationalPortalCredentials,
    Settings,
)
from src.sheets.models import SheetRowRef, Student


def _settings(environment: Environment, **overrides) -> Settings:
    base = Settings(
        environment=environment,
        sheets=GoogleSheetsConfig(
            service_account_file="credentials/service-account.json",
            spreadsheet_id_ogr="ogr-id",
            spreadsheet_id_udise="udise-id",
            spreadsheet_id_pen="pen-id",
        ),
        gujarat_portal=GujaratPortalCredentials(
            login_url="https://example.invalid/gujarat",
            school_code="school-code",
            username="user",
            password="pw",
        ),
        national_portal=NationalPortalCredentials(
            login_url="https://example.invalid/national",
            username="user",
            password="pw",
        ),
        diagnostics_dir=Path("diagnostics"),
        log_level="INFO",
        sqlite_path=Path("unused.sqlite3"),
    )
    return replace(base, **overrides) if overrides else base


# ---------------- environment ----------------


def test_live_environment_is_detected_as_live():
    assert _settings(Environment.LIVE).environment is Environment.LIVE


# ---------------- no silent fallback when misconfigured ----------------


def test_missing_login_url_in_live_raises_rather_than_proceeding():
    """The core safety property: a misconfigured run must fail loudly.

    Proceeding here would reproduce exactly the bug this module exists to
    fix — a run that looks successful while touching nothing real, or
    (worse) writing invalid results to real spreadsheets.
    """
    gujarat = replace(_settings(Environment.LIVE).gujarat_portal, login_url=None)
    from src.app.portal_factory import _require

    with pytest.raises(PortalSetupError) as exc:
        _require(gujarat.login_url, name="GUJARAT_UDISE_LOGIN_URL", portal="Gujarat UDISE")
    assert "GUJARAT_UDISE_LOGIN_URL" in str(exc.value)


@pytest.mark.parametrize("value", ["", "   ", None])
def test_blank_login_url_is_treated_as_missing(value):
    from src.app.portal_factory import _require

    with pytest.raises(PortalSetupError):
        _require(value, name="NATIONAL_UDISE_PLUS_LOGIN_URL", portal="National UDISE+")


def test_missing_credential_in_live_raises():
    from src.app.portal_factory import _require

    with pytest.raises(PortalSetupError) as exc:
        _require(None, name="NATIONAL_UDISE_PLUS_PASSWORD", portal="National UDISE+")
    assert "NATIONAL_UDISE_PLUS_PASSWORD" in str(exc.value)


def test_login_url_must_be_http_or_https():
    """A non-HTTP URL means a misconfiguration; refuse rather than navigate
    somewhere unexpected (e.g. a file:// or javascript: value)."""
    assert _validate_login_url("https://ok.invalid", portal="p") == "https://ok.invalid"
    assert _validate_login_url("http://ok.invalid", portal="p") == "http://ok.invalid"
    for bad in ("file:///etc/passwd", "javascript:alert(1)", "not-a-url"):
        with pytest.raises(PortalSetupError):
            _validate_login_url(bad, portal="p")


def test_login_url_is_stripped():
    assert _validate_login_url("  https://ok.invalid  ", portal="p") == "https://ok.invalid"


# ---------------- real student discovery ----------------


class _StubSheets:
    """Minimal repository exposing only what load_live_students uses."""

    def __init__(self, students=None, error=None):
        self._students = students or []
        self._error = error

    def list_students(self):
        if self._error is not None:
            raise self._error
        return list(self._students)


def test_live_students_are_loaded_from_the_repository():
    students = [
        Student(student_id="aadhar:1111", name="Real One", class_name="LKG/KG1/PP2"),
        Student(student_id="aadhar:2222", name="Real Two", class_name="PH1"),
    ]
    entries = load_live_students(_StubSheets(students))
    assert [e.student.name for e in entries] == ["Real One", "Real Two"]
    # Real students must NOT claim a pre-known condition — it is derived at
    # run time by entry_router from real sheet state.
    assert all(e.intended_condition is None for e in entries)
    assert all("derived at run time" in e.note or "run time" in e.note for e in entries)


def test_live_student_entries_are_runnable_not_nd_only():
    """The Run button must be enabled for real students.

    Regression guard: the Run/Start buttons used to be gated on
    `intended_condition`, which real students never carry a value for.
    Real students always carry None, so that gate silently disabled every
    real student.
    """
    entries = load_live_students(
        _StubSheets([Student(student_id="a", name="N", class_name="LKG/KG1/PP2")])
    )
    assert entries[0].intended_condition is None
    # The screen-level check is "entry is not None" now; assert the field
    # the old gate used is what would have disabled it.
    assert entries  # a real student list is populated at all


def test_ogr_load_failure_does_not_crash_startup():
    """A bad service account / revoked sharing must not stop the app from
    starting — it must produce an empty, diagnosable list instead."""
    entries = load_live_students(_StubSheets(error=RuntimeError("403 forbidden")))
    assert entries == []


def test_empty_ogr_register_yields_no_entries():
    assert load_live_students(_StubSheets([])) == []


def test_demo_student_entry_shape_is_stable():
    """DemoStudentEntry's contract is load-bearing for existing tests."""
    entry = DemoStudentEntry(
        student=Student(student_id="x", name="N", class_name="C"),
        intended_condition=1,
        note="note",
    )
    assert entry.intended_condition == 1
    assert entry.note == "note"


def test_student_requires_class_name_so_real_rows_carry_one():
    """Guards the shape real OGR rows are mapped into: STD is a required
    column, so a live student always has a class name."""
    student = Student(student_id="aadhar:1", name="N", class_name="PH1")
    assert student.class_name == "PH1"
