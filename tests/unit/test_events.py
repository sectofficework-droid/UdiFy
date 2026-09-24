"""Unit tests for the append-only pen_case_events log (src/db/events.py)."""

from __future__ import annotations

import sqlite3

import pytest

from src.db.connection import connect
from src.db.events import (
    CaseStatus,
    EventCode,
    InvalidTransitionError,
    MissingRequiredFieldError,
    PenCaseEvent,
    Performer,
    append_event,
    get_case_history,
    get_current_status,
)


@pytest.fixture()
def conn(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    connection = connect(db_path)
    yield connection
    connection.close()


def _base_event(**overrides) -> PenCaseEvent:
    defaults = dict(
        case_id="case-1",
        student_id="student-1",
        student_name="Test Student",
        workflow="PEN_NEW_ENTRY",
        event_code=EventCode.PEN_ACTION_REQUIRED_OPENED,
        case_status_before=CaseStatus.ACTION_REQUIRED,
        case_status_after=CaseStatus.ACTION_REQUIRED,
        spreadsheet_status="PENDING",
        spreadsheet_color="NONE",
        performed_by=Performer.AUTOMATION,
        environment="MOCK",
    )
    defaults.update(overrides)
    return PenCaseEvent(**defaults)


def test_append_and_read_back(conn: sqlite3.Connection):
    event_id = append_event(conn, _base_event())
    history = get_case_history(conn, "case-1")
    assert len(history) == 1
    assert history[0]["event_id"] == event_id
    assert history[0]["environment"] == "MOCK"
    assert history[0]["event_hash"] is not None
    assert history[0]["previous_event_hash"] is None


def test_valid_transition_recorded(conn: sqlite3.Connection):
    append_event(conn, _base_event())
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_VERIFICATION_STARTED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.VERIFYING,
        ),
    )
    assert get_current_status(conn, "case-1") == CaseStatus.VERIFYING
    assert len(get_case_history(conn, "case-1")) == 2


def test_invalid_transition_rejected_but_logged(conn: sqlite3.Connection):
    append_event(conn, _base_event())
    with pytest.raises(InvalidTransitionError):
        append_event(
            conn,
            _base_event(
                event_code=EventCode.PEN_RESOLVED,
                case_status_before=CaseStatus.ACTION_REQUIRED,
                case_status_after=CaseStatus.RESOLVED,
                resolution_note="not actually allowed from ACTION_REQUIRED",
            ),
        )
    # The rejected attempt is still on the record, per spec §R.
    history = get_case_history(conn, "case-1")
    assert len(history) == 2
    assert history[-1]["event_code"] == EventCode.PEN_INVALID_TRANSITION_ATTEMPT.value
    # And the case status did NOT actually change.
    assert get_current_status(conn, "case-1") == CaseStatus.ACTION_REQUIRED


def test_resolved_requires_resolution_note(conn: sqlite3.Connection):
    append_event(conn, _base_event())
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_VERIFICATION_STARTED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.VERIFYING,
        ),
    )
    with pytest.raises(MissingRequiredFieldError):
        append_event(
            conn,
            _base_event(
                event_code=EventCode.PEN_RESOLVED,
                case_status_before=CaseStatus.VERIFYING,
                case_status_after=CaseStatus.RESOLVED,
                resolution_note=None,
            ),
        )


def test_reopen_requires_reopen_reason(conn: sqlite3.Connection):
    append_event(conn, _base_event())
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_VERIFICATION_STARTED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.VERIFYING,
        ),
    )
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_RESOLVED,
            case_status_before=CaseStatus.VERIFYING,
            case_status_after=CaseStatus.RESOLVED,
            resolution_note="closed, PEN confirmed",
        ),
    )
    with pytest.raises(MissingRequiredFieldError):
        append_event(
            conn,
            _base_event(
                event_code=EventCode.PEN_CASE_REOPENED,
                case_status_before=CaseStatus.RESOLVED,
                case_status_after=CaseStatus.REOPENED,
                reopen_reason=None,
            ),
        )
    # With the reason, it succeeds and a NEW cycle is used (history preserved).
    new_cycle = "cycle-2"
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_CASE_REOPENED,
            case_status_before=CaseStatus.RESOLVED,
            case_status_after=CaseStatus.REOPENED,
            reopen_reason="portal status changed after resolution",
            case_cycle_id=new_cycle,
        ),
    )
    history = get_case_history(conn, "case-1")
    # 3 events in cycle 1 (open, verify, resolve) + 1 in cycle 2 (reopen).
    assert len(history) == 4
    assert history[0]["case_cycle_id"] != history[-1]["case_cycle_id"]


def test_manual_action_completed_requires_description(conn: sqlite3.Connection):
    append_event(conn, _base_event())
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_MANUAL_ACTION_STARTED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.MANUAL_REVIEW,
        ),
    )
    with pytest.raises(MissingRequiredFieldError):
        append_event(
            conn,
            _base_event(
                event_code=EventCode.PEN_MANUAL_ACTION_COMPLETED,
                case_status_before=CaseStatus.MANUAL_REVIEW,
                case_status_after=CaseStatus.MANUAL_REVIEW,
                action_description=None,
            ),
        )


def test_hash_chain_links_events(conn: sqlite3.Connection):
    append_event(conn, _base_event())
    append_event(
        conn,
        _base_event(
            event_code=EventCode.PEN_VERIFICATION_STARTED,
            case_status_before=CaseStatus.ACTION_REQUIRED,
            case_status_after=CaseStatus.VERIFYING,
        ),
    )
    history = get_case_history(conn, "case-1")
    assert history[1]["previous_event_hash"] == history[0]["event_hash"]
