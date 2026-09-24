"""Google Sheets adapter interface + mock/real implementations.

Business logic (the workflow engine) depends on StudentSheetRepository,
never on the Google Sheets SDK directly (mock-first decision, master
spec "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION" §2):

    StudentSheetRepository
            |
            +-- GoogleSheetsRepository   (real)
            +-- MockSheetsRepository     (in-memory; the workflow engine
                                           must run completely against
                                           this one)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from src.diagnostics.logging_setup import get_logger, log_event
from src.sheets.models import SheetRowRef, Student

_logger = get_logger("sheets")

# Row-state/color vocabulary (DB-DESIGN.md §A.4) — never invent a new one.
GREEN = "GREEN"
LIGHT_ORANGE = "LIGHT_ORANGE"
UNCHANGED = "UNCHANGED"


class SheetWriteError(Exception):
    """A write failed. Never silently retried by the repository itself —
    the caller (workflow engine) decides whether/how to retry, per the
    retry-safety rule (spec Final Authority §G)."""


class SheetVerificationError(Exception):
    """A write appeared to succeed but re-reading the cell didn't confirm
    it. Never treated as success (spec Final Authority §J)."""


class StudentSheetRepository(Protocol):
    def find_by_name(
        self, name: str, class_name: str | None = None
    ) -> list[Student]: ...

    def find_by_uid(self, uid: str) -> Student | None: ...

    def find_by_pen(self, pen: str) -> Student | None: ...

    def get_row_values(self, row_ref: SheetRowRef) -> dict[str, str]: ...

    def get_row_color(self, row_ref: SheetRowRef) -> str: ...

    def write_cell(self, row_ref: SheetRowRef, column: str, value: str) -> None: ...

    def set_row_color(self, row_ref: SheetRowRef, color: str) -> None: ...

    def verify_cell(
        self, row_ref: SheetRowRef, column: str, expected_value: str
    ) -> bool: ...


@dataclass
class _MockRow:
    values: dict[str, str] = field(default_factory=dict)
    color: str = UNCHANGED


class MockSheetsRepository:
    """In-memory StudentSheetRepository for tests and mock-mode runs.

    Every write is idempotent: writing the same value/color again is a
    no-op that doesn't count as a new "change" (see write_log), matching
    the spec's duplicate-update-prevention requirement (decision §2).
    """

    def __init__(self) -> None:
        self._students: dict[str, Student] = {}
        self._rows: dict[tuple[str, str, int], _MockRow] = {}
        self.write_log: list[tuple[str, str, str]] = []  # (row key, column/color, value)
        self._fail_next_write = False
        self._fail_next_verify = False
        self._network_down = False

    # -- test-only fault injection ---------------------------------
    def simulate_write_failure(self, times: int = 1) -> None:
        self._fail_next_write = times

    def simulate_verification_failure(self, times: int = 1) -> None:
        self._fail_next_verify = times

    def simulate_network_failure(self, down: bool = True) -> None:
        self._network_down = down

    # -- seeding for tests -------------------------------------------
    def seed_student(self, student: Student) -> None:
        self._students[student.student_id] = student
        for row_ref in (student.ogr_row, student.udise_row, student.pen_row):
            if row_ref is not None:
                key = (row_ref.spreadsheet, row_ref.tab, row_ref.row_number)
                self._rows.setdefault(key, _MockRow())

    def _row_key(self, row_ref: SheetRowRef) -> tuple[str, str, int]:
        return (row_ref.spreadsheet, row_ref.tab, row_ref.row_number)

    def _check_network(self) -> None:
        if self._network_down:
            log_event(
                _logger, logging.WARNING, "sheets network failure",
                error_code="SHEETS_NETWORK_FAILURE", retryable=True,
            )
            raise SheetWriteError("simulated network failure")

    # -- StudentSheetRepository ---------------------------------------
    def find_by_name(
        self, name: str, class_name: str | None = None
    ) -> list[Student]:
        self._check_network()
        return [
            s
            for s in self._students.values()
            if s.name.strip().lower() == name.strip().lower()
            and (class_name is None or s.class_name == class_name)
        ]

    def find_by_uid(self, uid: str) -> Student | None:
        self._check_network()
        for s in self._students.values():
            if s.uid_udise == uid:
                return s
        return None

    def find_by_pen(self, pen: str) -> Student | None:
        self._check_network()
        for s in self._students.values():
            if s.pen == pen:
                return s
        return None

    def get_row_values(self, row_ref: SheetRowRef) -> dict[str, str]:
        self._check_network()
        row = self._rows.get(self._row_key(row_ref), _MockRow())
        return dict(row.values)

    def get_row_color(self, row_ref: SheetRowRef) -> str:
        self._check_network()
        row = self._rows.get(self._row_key(row_ref), _MockRow())
        return row.color

    def write_cell(self, row_ref: SheetRowRef, column: str, value: str) -> None:
        self._check_network()
        if self._fail_next_write:
            self._fail_next_write -= 1
            log_event(
                _logger, logging.ERROR, "sheet cell write failed",
                error_code="SHEETS_WRITE_FAILED", column=column,
                row_ref=str(self._row_key(row_ref)), retryable=True,
            )
            raise SheetWriteError(f"simulated write failure on {column}")
        key = self._row_key(row_ref)
        row = self._rows.setdefault(key, _MockRow())
        if row.values.get(column) == value:
            return  # idempotent no-op — already this value
        row.values[column] = value
        self.write_log.append((str(key), column, value))
        log_event(
            _logger, logging.INFO, "sheet cell written",
            column=column, row_ref=str(key),
        )

    def set_row_color(self, row_ref: SheetRowRef, color: str) -> None:
        self._check_network()
        if self._fail_next_write:
            self._fail_next_write -= 1
            log_event(
                _logger, logging.ERROR, "row color write failed",
                error_code="SHEETS_WRITE_FAILED", target_color=color,
                row_ref=str(self._row_key(row_ref)), retryable=True,
            )
            raise SheetWriteError("simulated write failure on row color")
        key = self._row_key(row_ref)
        row = self._rows.setdefault(key, _MockRow())
        if row.color == color:
            return  # idempotent no-op
        row.color = color
        self.write_log.append((str(key), "__color__", color))
        log_event(
            _logger, logging.INFO, "row color written",
            color=color, row_ref=str(key),
        )

    def verify_cell(
        self, row_ref: SheetRowRef, column: str, expected_value: str
    ) -> bool:
        self._check_network()
        if self._fail_next_verify:
            self._fail_next_verify -= 1
            log_event(
                _logger, logging.WARNING, "cell verification failed",
                column=column, row_ref=str(self._row_key(row_ref)),
            )
            return False
        row = self._rows.get(self._row_key(row_ref), _MockRow())
        return row.values.get(column) == expected_value


class GoogleSheetsRepository:
    """Real Google Sheets implementation (google-api-python-client).

    Code-complete but not live-tested without credentials — per the
    mock-first decision, this class is built now and exercised only at
    the Live Verification Gate (TODO.md). Never instantiate this in mock
    mode; the workflow engine takes whichever repository it's given via
    dependency injection, it never chooses.
    """

    def __init__(self, service_account_file: str, spreadsheet_ids: dict[str, str]):
        self._service_account_file = service_account_file
        self._spreadsheet_ids = spreadsheet_ids
        self._service = None  # lazily built in _client(); never at import time

    def _client(self):
        if self._service is None:
            # Imported lazily so mock-mode/tests never require google-api
            # network setup or credentials to even import this module.
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_file(
                self._service_account_file,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def find_by_name(
        self, name: str, class_name: str | None = None
    ) -> list[Student]:
        raise NotImplementedError(
            "GoogleSheetsRepository.find_by_name: implement against the real "
            "OGR/UDISE/PEN sheets at the Live Verification Gate "
            "(TODO.md phase L2) — not before, per the mock-first decision."
        )

    def find_by_uid(self, uid: str) -> Student | None:
        raise NotImplementedError("see find_by_name")

    def find_by_pen(self, pen: str) -> Student | None:
        raise NotImplementedError("see find_by_name")

    def get_row_values(self, row_ref: SheetRowRef) -> dict[str, str]:
        raise NotImplementedError("see find_by_name")

    def get_row_color(self, row_ref: SheetRowRef) -> str:
        raise NotImplementedError("see find_by_name")

    def write_cell(self, row_ref: SheetRowRef, column: str, value: str) -> None:
        raise NotImplementedError("see find_by_name")

    def set_row_color(self, row_ref: SheetRowRef, color: str) -> None:
        raise NotImplementedError("see find_by_name")

    def verify_cell(
        self, row_ref: SheetRowRef, column: str, expected_value: str
    ) -> bool:
        raise NotImplementedError("see find_by_name")
