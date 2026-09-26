"""Unit tests for src/db/workflow_runs.py — the checkpoint/crash-persistence
layer behind spec §13's "pause and resume from checkpoint" requirement and
the New UDISE/New PEN duplicate-submission guards in src/engine/branches.py.
"""

from __future__ import annotations

import pytest

from src.db.connection import connect
from src.db.students import upsert_student
from src.db.workflow_runs import (
    complete_run,
    find_incomplete_run_with_checkpoint_flag,
    patch_checkpoint,
    start_run,
)
from src.sheets.models import Student


@pytest.fixture()
def db_conn(tmp_path):
    conn = connect(tmp_path / "test.sqlite3")
    yield conn
    conn.close()


def _seed_student(conn, student_id="s-wf-1") -> Student:
    student = Student(student_id=student_id, name="WF Student", class_name="LKG/KG1/PP2")
    upsert_student(conn, student)
    return student


def test_start_run_creates_an_incomplete_row(db_conn):
    student = _seed_student(db_conn)
    start_run(
        db_conn, run_id="r1", student_id=student.student_id, condition="TEST_COND",
        environment="MOCK", current_state="STARTED",
    )
    row = db_conn.execute("SELECT * FROM workflow_runs WHERE run_id = ?", ("r1",)).fetchone()
    assert row is not None
    assert row["completed_at"] is None
    assert row["current_state"] == "STARTED"


def test_patch_checkpoint_merges_rather_than_overwrites(db_conn):
    student = _seed_student(db_conn)
    start_run(
        db_conn, run_id="r2", student_id=student.student_id, condition="TEST_COND",
        environment="MOCK", current_state="STARTED",
    )
    patch_checkpoint(db_conn, run_id="r2", patch={"a": 1})
    patch_checkpoint(db_conn, run_id="r2", patch={"b": 2}, current_state="MID")

    row = db_conn.execute(
        "SELECT current_state, checkpoint_json FROM workflow_runs WHERE run_id = ?", ("r2",)
    ).fetchone()
    assert row["current_state"] == "MID"
    import json
    assert json.loads(row["checkpoint_json"]) == {"a": 1, "b": 2}


def test_complete_run_sets_completed_at(db_conn):
    student = _seed_student(db_conn)
    start_run(
        db_conn, run_id="r3", student_id=student.student_id, condition="TEST_COND",
        environment="MOCK", current_state="STARTED",
    )
    complete_run(db_conn, run_id="r3")
    row = db_conn.execute(
        "SELECT completed_at FROM workflow_runs WHERE run_id = ?", ("r3",)
    ).fetchone()
    assert row["completed_at"] is not None


def test_find_incomplete_run_with_checkpoint_flag_ignores_completed_runs(db_conn):
    student = _seed_student(db_conn)
    start_run(
        db_conn, run_id="r4", student_id=student.student_id, condition="TEST_COND",
        environment="MOCK", current_state="STARTED",
    )
    patch_checkpoint(db_conn, run_id="r4", patch={"udise_new_entered": True})
    complete_run(db_conn, run_id="r4")

    found = find_incomplete_run_with_checkpoint_flag(
        db_conn, student_id=student.student_id, flag_key="udise_new_entered",
    )
    assert found is None  # completed — not a candidate for resume/guard logic


def test_find_incomplete_run_with_checkpoint_flag_finds_a_matching_incomplete_run(db_conn):
    student = _seed_student(db_conn)
    start_run(
        db_conn, run_id="r5", student_id=student.student_id, condition="TEST_COND",
        environment="MOCK", current_state="STARTED",
    )
    patch_checkpoint(db_conn, run_id="r5", patch={"pen_new_entered": True})

    found = find_incomplete_run_with_checkpoint_flag(
        db_conn, student_id=student.student_id, flag_key="pen_new_entered",
    )
    assert found is not None
    assert found.run_id == "r5"

    not_found = find_incomplete_run_with_checkpoint_flag(
        db_conn, student_id=student.student_id, flag_key="udise_new_entered",
    )
    assert not_found is None  # different flag, never set on this run


def test_find_incomplete_run_ignores_other_students(db_conn):
    student_a = _seed_student(db_conn, "s-wf-a")
    _seed_student(db_conn, "s-wf-b")
    start_run(
        db_conn, run_id="r6", student_id=student_a.student_id, condition="TEST_COND",
        environment="MOCK", current_state="STARTED",
    )
    patch_checkpoint(db_conn, run_id="r6", patch={"udise_new_entered": True})

    found = find_incomplete_run_with_checkpoint_flag(
        db_conn, student_id="s-wf-b", flag_key="udise_new_entered",
    )
    assert found is None
