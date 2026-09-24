"""Unit tests for MockSheetsRepository (src/sheets/repository.py).

Covers the mock-testing requirements from the mock-first decision
(master spec "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION" §2).
"""

from __future__ import annotations

import pytest

from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import (
    GREEN,
    LIGHT_ORANGE,
    MockSheetsRepository,
    SheetWriteError,
)


@pytest.fixture()
def repo() -> MockSheetsRepository:
    r = MockSheetsRepository()
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    student = Student(
        student_id="s-1",
        name="Kabir Rana",
        class_name="SR KG",
        father_name="Naresh Rana",
        gr_no="P114",
        udise_row=row,
    )
    r.seed_student(student)
    return r


def test_find_by_name(repo: MockSheetsRepository):
    results = repo.find_by_name("Kabir Rana")
    assert len(results) == 1
    assert results[0].student_id == "s-1"


def test_find_by_name_case_insensitive_and_class_filtered(repo: MockSheetsRepository):
    assert repo.find_by_name("kabir rana", class_name="SR KG")
    assert not repo.find_by_name("kabir rana", class_name="1st")


def test_find_by_uid_and_pen_when_absent(repo: MockSheetsRepository):
    assert repo.find_by_uid("242241000672631042") is None
    assert repo.find_by_pen("23060471198") is None


def test_write_cell_and_read_row_values(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.write_cell(row, "UDISE No", "242241000672631042")
    values = repo.get_row_values(row)
    assert values["UDISE No"] == "242241000672631042"


def test_write_cell_preserves_other_values(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.write_cell(row, "UDISE No", "242241000672631042")
    repo.write_cell(row, "Class", "SR KG")
    values = repo.get_row_values(row)
    assert values["UDISE No"] == "242241000672631042"
    assert values["Class"] == "SR KG"


def test_set_row_color_and_read_back(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    assert repo.get_row_color(row) == "UNCHANGED"
    repo.set_row_color(row, GREEN)
    assert repo.get_row_color(row) == GREEN


def test_duplicate_write_is_idempotent_noop(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.write_cell(row, "UDISE No", "242241000672631042")
    repo.write_cell(row, "UDISE No", "242241000672631042")  # duplicate
    # Only one real write should be logged — the second is a no-op.
    assert len(repo.write_log) == 1


def test_duplicate_color_write_is_idempotent_noop(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.set_row_color(row, LIGHT_ORANGE)
    repo.set_row_color(row, LIGHT_ORANGE)
    assert repo.write_log.count((str((row.spreadsheet, row.tab, row.row_number)), "__color__", LIGHT_ORANGE)) == 1


def test_simulated_write_failure_raises(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.simulate_write_failure(times=1)
    with pytest.raises(SheetWriteError):
        repo.write_cell(row, "UDISE No", "242241000672631042")
    # Retry (no fault this time) should succeed.
    repo.write_cell(row, "UDISE No", "242241000672631042")
    assert repo.get_row_values(row)["UDISE No"] == "242241000672631042"


def test_simulated_network_failure_raises_on_reads_and_writes(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.simulate_network_failure(True)
    with pytest.raises(SheetWriteError):
        repo.write_cell(row, "UDISE No", "x")
    with pytest.raises(SheetWriteError):
        repo.get_row_values(row)
    repo.simulate_network_failure(False)
    repo.write_cell(row, "UDISE No", "x")  # now succeeds


def test_verify_cell_success_and_simulated_failure(repo: MockSheetsRepository):
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.write_cell(row, "UDISE No", "242241000672631042")
    assert repo.verify_cell(row, "UDISE No", "242241000672631042") is True

    repo.simulate_verification_failure(times=1)
    assert repo.verify_cell(row, "UDISE No", "242241000672631042") is False
    # Failure injection is one-shot — next call succeeds again.
    assert repo.verify_cell(row, "UDISE No", "242241000672631042") is True
