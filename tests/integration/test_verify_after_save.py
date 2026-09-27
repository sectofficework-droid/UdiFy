"""Tests for verify-after-uncertain-save.

The behaviour under test is a safety rule, not a convenience: when a
portal save's outcome is unknown, the app must re-read state and escalate
— never click Save again. On a one-shot government action, a repeat click
is how a duplicate student record gets created.
"""

from __future__ import annotations

import pytest

from src.db.connection import connect
from src.db.schema import initialize_database
from src.engine.verify_after_save import UnverifiedActionError, verify_or_report
from src.sheets.models import Student


@pytest.fixture()
def conn():
    connection = connect(":memory:")
    initialize_database(connection)
    yield connection
    connection.close()


@pytest.fixture()
def student():
    return Student(student_id="aadhar:111122223333", name="Verify Test", class_name="SR.KG")


class _Counter:
    """A read-only probe that records how many times it was called.

    Once its scripted answers run out it keeps returning the LAST answer,
    so a test that scripts a single `False` means "never confirmed" rather
    than "confirmed on the second call".
    """

    def __init__(self, answers):
        if not answers:
            raise ValueError("script at least one answer")
        self.answers = list(answers)
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        if len(self.answers) > 1:
            return bool(self.answers.pop(0))
        return bool(self.answers[0])


# ---------------- the confirmed path ----------------


def test_confirmed_action_returns_without_escalating(conn, student):
    probe = _Counter([True])
    verify_or_report(
        conn, student=student, action_description="Save Student", probe=probe
    )
    assert probe.calls == 1


def test_probe_is_retried_when_the_page_is_slow(conn, student):
    """A confirmation that appears on the second read must not be
    misreported as a failure."""
    probe = _Counter([False, True])
    verify_or_report(
        conn, student=student, action_description="Save Student", probe=probe
    )
    assert probe.calls == 2


# ---------------- the unconfirmed path ----------------


def test_unconfirmed_action_raises_rather_than_reporting_success(conn, student):
    probe = _Counter([False])
    with pytest.raises(UnverifiedActionError):
        verify_or_report(
            conn, student=student, action_description="Save Student", probe=probe
        )


def test_probe_is_bounded_by_max_probes(conn, student):
    probe = _Counter([False] * 10)
    with pytest.raises(UnverifiedActionError):
        verify_or_report(
            conn, student=student, action_description="Save Student", probe=probe
        )
    assert probe.calls == 3, "must not probe indefinitely"


def test_error_message_tells_the_operator_not_to_rerun(conn, student):
    probe = _Counter([False])
    with pytest.raises(UnverifiedActionError) as exc:
        verify_or_report(
            conn, student=student, action_description="Add New Student", probe=probe
        )
    message = str(exc.value)
    assert "NOT been repeated" in message
    assert "duplicate" in message.lower()


def test_raising_probe_is_treated_as_unconfirmed_not_success(conn, student):
    def exploding_probe():
        raise RuntimeError("page gone")

    with pytest.raises(UnverifiedActionError):
        verify_or_report(
            conn, student=student, action_description="Save Student", probe=exploding_probe
        )


# ---------------- auditability ----------------


def test_unconfirmed_action_is_recorded_in_the_audit_trail(conn, student):
    from src.db.events import get_case_history

    probe = _Counter([False])
    with pytest.raises(UnverifiedActionError):
        verify_or_report(
            conn, student=student, action_description="Save Student", probe=probe
        )

    history = get_case_history(conn, student.student_id)
    assert history, "an unverified action must leave an audit record"
    event = history[-1]
    assert event["portal_status"] == "UNCONFIRMED"
    assert "NOT repeated" in (event["resolution_note"] or "") or "not" in (
        event["resolution_note"] or ""
    ).lower()


def test_confirmed_action_records_no_failure_event(conn, student):
    from src.db.events import get_case_history

    verify_or_report(
        conn, student=student, action_description="Save Student", probe=_Counter([True])
    )
    history = get_case_history(conn, student.student_id)
    failures = [
        e for e in history if e["error_code"] == "ACTION_UNVERIFIED"
    ]
    assert not failures


# ---------------- the structural guarantee ----------------


def test_verify_function_cannot_repeat_an_action():
    """No mutating callable is accepted — only a read-only probe. This is
    what makes "never repeat" a property of the code, not a habit."""
    import inspect

    params = inspect.signature(verify_or_report).parameters
    for forbidden in ("action", "submit", "click", "retry_action", "adapter", "page"):
        assert forbidden not in params, forbidden
    assert "probe" in params
