"""Automated entry-condition determination (spec §78/§79's decision tree)
+ dispatch — previously a real, honestly-flagged gap (TODO.md acceptance
criteria: "Correct entry-condition routing (1-4)"): every condition
engine was correct once selected, but nothing picked *which* one to run
from a student's actual sheet state — the caller had to already know.

Spec §79's decision tree is a strict binary per side (UDISE: NEW or
IMPORT; PEN: NEW or IMPORT), which is exactly Conditions 1-4. This module
adds one more state per side — ALREADY_COMPLETE (row already GREEN) — to
also satisfy the "Already-GREEN row is skipped" acceptance criterion
(spec §264) in the same place, since both requirements read the same
sheet state. Any combination the decision tree doesn't define (e.g. one
side already GREEN, the other IMPORT-pending) is never guessed into the
nearest condition — it's reported AMBIGUOUS for manual review, per the
project's standing "never guess an unconfirmed state" rule.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum

from src.engine.condition1 import Condition1Engine, Condition1Result
from src.engine.condition2 import Condition2Engine, Condition2Result
from src.engine.condition3 import Condition3Engine, Condition3Result
from src.engine.condition4 import Condition4Engine, Condition4Result
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter
from src.sheets.models import Student
from src.sheets.repository import GREEN, StudentSheetRepository


class UdiseState(str, Enum):
    NEW = "NEW"
    IMPORT_PENDING = "IMPORT_PENDING"
    ALREADY_COMPLETE = "ALREADY_COMPLETE"


class PenState(str, Enum):
    NEW = "NEW"
    IMPORT_PENDING = "IMPORT_PENDING"
    ALREADY_COMPLETE = "ALREADY_COMPLETE"


class EntryCondition(str, Enum):
    CONDITION_1 = "CONDITION_1"
    CONDITION_2 = "CONDITION_2"
    CONDITION_3 = "CONDITION_3"
    CONDITION_4 = "CONDITION_4"
    ALREADY_COMPLETE = "ALREADY_COMPLETE"  # both sides GREEN — skip (spec §264)
    AMBIGUOUS = "AMBIGUOUS"  # not one of the 4 defined combinations — manual review


@dataclass(frozen=True)
class RoutingDecision:
    udise_state: UdiseState
    pen_state: PenState
    condition: EntryCondition


def determine_udise_state(sheets: StudentSheetRepository, student: Student) -> UdiseState:
    if student.udise_row is None:
        return UdiseState.NEW
    if sheets.get_row_color(student.udise_row) == GREEN:
        return UdiseState.ALREADY_COMPLETE
    if student.uid_udise:
        # A known UID (e.g. from a Transfer Certificate) not yet reflected
        # as GREEN means the UDISE Import/transfer-request action is
        # still pending (spec §X) — this is the tree's "IMPORT" branch.
        return UdiseState.IMPORT_PENDING
    return UdiseState.NEW


def determine_pen_state(sheets: StudentSheetRepository, student: Student) -> PenState:
    if student.pen_row is None:
        return PenState.NEW
    if sheets.get_row_color(student.pen_row) == GREEN:
        return PenState.ALREADY_COMPLETE
    if student.aadhaar:
        # spec §6: a duplicate-Aadhaar signal is what routes a student to
        # the PEN Import — Other School ACTIVE branch, not a UI choice.
        return PenState.IMPORT_PENDING
    return PenState.NEW


_TREE: dict[tuple[UdiseState, PenState], EntryCondition] = {
    (UdiseState.NEW, PenState.NEW): EntryCondition.CONDITION_1,
    (UdiseState.NEW, PenState.IMPORT_PENDING): EntryCondition.CONDITION_2,
    (UdiseState.ALREADY_COMPLETE, PenState.NEW): EntryCondition.CONDITION_3,
    (UdiseState.IMPORT_PENDING, PenState.IMPORT_PENDING): EntryCondition.CONDITION_4,
}


def determine_entry_condition(sheets: StudentSheetRepository, student: Student) -> RoutingDecision:
    """spec §78 DETERMINE_ENTRY_CONDITION state, made a real, tested
    function instead of an implicit caller decision."""
    udise_state = determine_udise_state(sheets, student)
    pen_state = determine_pen_state(sheets, student)

    if udise_state is UdiseState.ALREADY_COMPLETE and pen_state is PenState.ALREADY_COMPLETE:
        condition = EntryCondition.ALREADY_COMPLETE
    else:
        condition = _TREE.get((udise_state, pen_state), EntryCondition.AMBIGUOUS)

    return RoutingDecision(udise_state=udise_state, pen_state=pen_state, condition=condition)


class AmbiguousEntryConditionError(Exception):
    """Raised by run_entry() when the sheet state doesn't match any of the
    4 defined conditions (or the already-complete skip) — never guessed
    into the nearest one."""


def run_entry(
    sheets: StudentSheetRepository,
    gujarat: GujaratUDISEPortalAdapter,
    national: NationalUDISEPortalAdapter,
    conn: sqlite3.Connection,
    student: Student,
    *,
    environment: str,
    section: str = "A",
) -> Condition1Result | Condition2Result | Condition3Result | Condition4Result | None:
    """Determines the entry condition from `student`'s current sheet
    state and runs the matching engine. Returns None (does nothing) for
    an already-GREEN-on-both-sides student (spec §264: skip during
    normal batch processing). Raises AmbiguousEntryConditionError for any
    other combination the decision tree doesn't define — the caller
    routes that to manual review, this function never guesses.
    """
    decision = determine_entry_condition(sheets, student)

    if decision.condition is EntryCondition.ALREADY_COMPLETE:
        return None

    if decision.condition is EntryCondition.AMBIGUOUS:
        raise AmbiguousEntryConditionError(
            f"{student.student_id!r}: UDISE state={decision.udise_state.value}, "
            f"PEN state={decision.pen_state.value} — not one of the 4 defined "
            "entry conditions; route to manual review rather than guess"
        )

    if decision.condition is EntryCondition.CONDITION_1:
        return Condition1Engine(sheets, gujarat, national, conn, environment).run(
            student, section=section
        )
    if decision.condition is EntryCondition.CONDITION_2:
        return Condition2Engine(sheets, gujarat, national, conn, environment).run(student)
    if decision.condition is EntryCondition.CONDITION_3:
        return Condition3Engine(sheets, national, conn, environment).run(student, section=section)
    if decision.condition is EntryCondition.CONDITION_4:
        return Condition4Engine(sheets, gujarat, national, conn, environment).run(student)

    raise AssertionError(f"Unhandled entry condition: {decision.condition}")  # pragma: no cover
