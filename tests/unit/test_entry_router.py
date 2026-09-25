"""Unit tests for src/engine/entry_router.py's automated entry-condition
determination (spec §78/§79 decision tree + §264 already-GREEN skip)."""

from __future__ import annotations

from src.engine.entry_router import (
    EntryCondition,
    PenState,
    UdiseState,
    determine_entry_condition,
    determine_pen_state,
    determine_udise_state,
)
from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import GREEN, MockSheetsRepository

UDISE_ROW = SheetRowRef("UDISE_Entry_(State)", "PH2", 1)
PEN_ROW = SheetRowRef("PEN_Entry_(National)", "PH2", 1)


def _student(**kwargs) -> Student:
    defaults = dict(
        student_id="s-router-1", name="Router Test Student", class_name="LKG/KG1/PP2",
        udise_row=UDISE_ROW, pen_row=PEN_ROW,
    )
    defaults.update(kwargs)
    return Student(**defaults)


def _sheets() -> MockSheetsRepository:
    repo = MockSheetsRepository()
    repo.seed_student(_student())
    return repo


def test_condition_1_both_sides_new():
    sheets = _sheets()
    decision = determine_entry_condition(sheets, _student())
    assert decision.udise_state is UdiseState.NEW
    assert decision.pen_state is PenState.NEW
    assert decision.condition is EntryCondition.CONDITION_1


def test_condition_2_new_udise_pen_import_signal():
    sheets = _sheets()
    student = _student(aadhaar="999988887777")
    decision = determine_entry_condition(sheets, student)
    assert decision.udise_state is UdiseState.NEW
    assert decision.pen_state is PenState.IMPORT_PENDING
    assert decision.condition is EntryCondition.CONDITION_2


def test_condition_3_udise_already_green_new_pen():
    sheets = _sheets()
    sheets.set_row_color(UDISE_ROW, GREEN)
    decision = determine_entry_condition(sheets, _student())
    assert decision.udise_state is UdiseState.ALREADY_COMPLETE
    assert decision.pen_state is PenState.NEW
    assert decision.condition is EntryCondition.CONDITION_3


def test_condition_4_both_sides_import_pending():
    sheets = _sheets()
    student = _student(uid_udise="OTHER-SCHOOL-UID-001", aadhaar="999988887777")
    decision = determine_entry_condition(sheets, student)
    assert decision.udise_state is UdiseState.IMPORT_PENDING
    assert decision.pen_state is PenState.IMPORT_PENDING
    assert decision.condition is EntryCondition.CONDITION_4


def test_already_complete_both_sides_green_is_skipped_not_a_condition():
    sheets = _sheets()
    sheets.set_row_color(UDISE_ROW, GREEN)
    sheets.set_row_color(PEN_ROW, GREEN)
    decision = determine_entry_condition(sheets, _student())
    assert decision.condition is EntryCondition.ALREADY_COMPLETE


def test_ambiguous_combination_is_never_guessed_into_a_condition():
    """UDISE already GREEN but PEN also needs an Import — not one of the
    4 defined conditions (Condition 3 pairs ALREADY_COMPLETE only with
    NEW PEN) — must not be silently treated as Condition 3 or 4."""
    sheets = _sheets()
    sheets.set_row_color(UDISE_ROW, GREEN)
    student = _student(aadhaar="999988887777")
    decision = determine_entry_condition(sheets, student)
    assert decision.condition is EntryCondition.AMBIGUOUS


def test_no_udise_row_at_all_is_treated_as_new():
    sheets = MockSheetsRepository()
    student = _student(udise_row=None)
    sheets.seed_student(student)
    assert determine_udise_state(sheets, student) is UdiseState.NEW


def test_no_pen_row_at_all_is_treated_as_new():
    sheets = MockSheetsRepository()
    student = _student(pen_row=None)
    sheets.seed_student(student)
    assert determine_pen_state(sheets, student) is PenState.NEW
