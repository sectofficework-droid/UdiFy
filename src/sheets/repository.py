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


def _col_letter(index: int) -> str:
    """0-based column index -> A1-style column letters (0 -> 'A', 26 -> 'AA')."""
    index += 1
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


@dataclass
class _TabMeta:
    sheet_id: int
    headers: dict[str, int]  # column header text -> 0-based column index


# Row-color swatches this app itself writes (Google Sheets standard palette
# "light green 2" / "light orange 1"). Not spec-mandated exact values —
# DB-DESIGN.md §A.4 defines the vocabulary, not the RGB — chosen here so
# writes and reads agree with each other. A row colored by hand before
# UdiFy touched it (e.g. legacy OGR highlighting) that doesn't match either
# swatch reads back as UNCHANGED rather than being guessed at; see the log
# line below for calibrating these constants against real sheet data at
# the Live Verification Gate (TODO.md phase L2).
_GREEN_RGB = (0.714, 0.843, 0.659)
_LIGHT_ORANGE_RGB = (0.953, 0.784, 0.412)
_COLOR_MATCH_TOLERANCE = 0.05


def _classify_bg_color(rgb: tuple[float, float, float] | None) -> str:
    if rgb is None:
        return UNCHANGED

    def _close(target: tuple[float, float, float]) -> bool:
        return all(abs(a - b) <= _COLOR_MATCH_TOLERANCE for a, b in zip(rgb, target))

    if _close(_GREEN_RGB):
        return GREEN
    if _close(_LIGHT_ORANGE_RGB):
        return LIGHT_ORANGE
    return UNCHANGED


class GoogleSheetsRepository:
    """Real Google Sheets implementation (google-api-python-client).

    Live-tested for connectivity only so far (Live Verification Gate L1,
    TODO.md) — read/write methods below are real, not stubs, but have not
    yet been exercised against the real OGR/UDISE/PEN sheets (that's L2).
    Never instantiate this in mock mode; the workflow engine takes
    whichever repository it's given via dependency injection, it never
    chooses.
    """

    def __init__(self, service_account_file: str, spreadsheet_ids: dict[str, str]):
        self._service_account_file = service_account_file
        self._spreadsheet_ids = spreadsheet_ids
        self._service = None  # lazily built in _client(); never at import time
        self._tab_meta_cache: dict[tuple[str, str], _TabMeta] = {}

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

    def _resolve_spreadsheet_id(self, spreadsheet_name: str) -> str:
        # SheetRowRef.spreadsheet is one of the three literal values used
        # across the codebase: "OGR", "UDISE_Entry_(State)",
        # "PEN_Entry_(National)" (models.py) — prefix-matched against the
        # {"OGR", "UDISE", "PEN"} keys app_context.py constructs this with.
        if spreadsheet_name.startswith("UDISE"):
            key = "UDISE"
        elif spreadsheet_name.startswith("PEN"):
            key = "PEN"
        else:
            key = "OGR"
        spreadsheet_id = self._spreadsheet_ids.get(key, "")
        if not spreadsheet_id:
            raise SheetWriteError(f"no spreadsheet ID configured for {key!r}")
        return spreadsheet_id

    def _row_ref_str(self, row_ref: SheetRowRef) -> str:
        return f"{row_ref.spreadsheet}/{row_ref.tab}/{row_ref.row_number}"

    def _tab_meta(self, spreadsheet_id: str, tab: str) -> _TabMeta:
        key = (spreadsheet_id, tab)
        cached = self._tab_meta_cache.get(key)
        if cached is not None:
            return cached
        service = self._client()
        sheet_meta = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties(sheetId,title)",
        ).execute()
        sheet_id = None
        for sheet in sheet_meta.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == tab:
                sheet_id = props.get("sheetId")
                break
        if sheet_id is None:
            raise SheetWriteError(f"tab {tab!r} not found in spreadsheet {spreadsheet_id}")
        header_result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"'{tab}'!1:1"
        ).execute()
        header_row = header_result.get("values", [[]])
        header_row = header_row[0] if header_row else []
        headers = {name: idx for idx, name in enumerate(header_row) if name}
        meta = _TabMeta(sheet_id=sheet_id, headers=headers)
        self._tab_meta_cache[key] = meta
        return meta

    def get_row_values(self, row_ref: SheetRowRef) -> dict[str, str]:
        spreadsheet_id = self._resolve_spreadsheet_id(row_ref.spreadsheet)
        meta = self._tab_meta(spreadsheet_id, row_ref.tab)
        if not meta.headers:
            return {}
        last_col = _col_letter(max(meta.headers.values()))
        range_ = f"'{row_ref.tab}'!A{row_ref.row_number}:{last_col}{row_ref.row_number}"
        result = self._client().spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_
        ).execute()
        rows = result.get("values", [[]])
        row = rows[0] if rows else []
        return {
            name: (row[idx] if idx < len(row) else "")
            for name, idx in meta.headers.items()
        }

    def get_row_color(self, row_ref: SheetRowRef) -> str:
        spreadsheet_id = self._resolve_spreadsheet_id(row_ref.spreadsheet)
        range_ = f"'{row_ref.tab}'!A{row_ref.row_number}"
        result = self._client().spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[range_],
            fields="sheets.data.rowData.values.userEnteredFormat.backgroundColor",
        ).execute()
        bg: dict = {}
        try:
            bg = (
                result["sheets"][0]["data"][0]["rowData"][0]["values"][0]
                .get("userEnteredFormat", {})
                .get("backgroundColor", {})
            )
        except (KeyError, IndexError):
            pass
        if not bg:
            return UNCHANGED
        rgb = (bg.get("red", 0.0), bg.get("green", 0.0), bg.get("blue", 0.0))
        color = _classify_bg_color(rgb)
        if color == UNCHANGED:
            log_event(
                _logger, logging.INFO, "unrecognized row background color",
                rgb=str(rgb), row_ref=self._row_ref_str(row_ref),
            )
        return color

    def write_cell(self, row_ref: SheetRowRef, column: str, value: str) -> None:
        spreadsheet_id = self._resolve_spreadsheet_id(row_ref.spreadsheet)
        meta = self._tab_meta(spreadsheet_id, row_ref.tab)
        if column not in meta.headers:
            raise SheetWriteError(
                f"column {column!r} not found in {row_ref.tab!r} headers: "
                f"{sorted(meta.headers)}"
            )
        col_letter = _col_letter(meta.headers[column])
        range_ = f"'{row_ref.tab}'!{col_letter}{row_ref.row_number}"
        try:
            self._client().spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_,
                valueInputOption="USER_ENTERED", body={"values": [[value]]},
            ).execute()
        except Exception as exc:
            log_event(
                _logger, logging.ERROR, "sheet cell write failed",
                error_code="SHEETS_WRITE_FAILED", column=column,
                row_ref=self._row_ref_str(row_ref), retryable=True,
            )
            raise SheetWriteError(f"failed to write {column!r}: {exc}") from exc
        log_event(
            _logger, logging.INFO, "sheet cell written",
            column=column, row_ref=self._row_ref_str(row_ref),
        )

    def set_row_color(self, row_ref: SheetRowRef, color: str) -> None:
        if color not in (GREEN, LIGHT_ORANGE):
            # No engine code ever writes UNCHANGED — it's a read-only
            # default state (DB-DESIGN.md §A.4) — so there's no swatch to
            # write for it.
            raise SheetWriteError(f"unsupported row color for a real write: {color!r}")
        spreadsheet_id = self._resolve_spreadsheet_id(row_ref.spreadsheet)
        meta = self._tab_meta(spreadsheet_id, row_ref.tab)
        if not meta.headers:
            raise SheetWriteError(
                f"no headers found for tab {row_ref.tab!r}; cannot size the color range"
            )
        end_col = max(meta.headers.values()) + 1
        rgb = _GREEN_RGB if color == GREEN else _LIGHT_ORANGE_RGB
        body = {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": meta.sheet_id,
                            "startRowIndex": row_ref.row_number - 1,
                            "endRowIndex": row_ref.row_number,
                            "startColumnIndex": 0,
                            "endColumnIndex": end_col,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": rgb[0],
                                    "green": rgb[1],
                                    "blue": rgb[2],
                                }
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            ]
        }
        try:
            self._client().spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
        except Exception as exc:
            log_event(
                _logger, logging.ERROR, "row color write failed",
                error_code="SHEETS_WRITE_FAILED", target_color=color,
                row_ref=self._row_ref_str(row_ref), retryable=True,
            )
            raise SheetWriteError(f"failed to set row color to {color}: {exc}") from exc
        log_event(
            _logger, logging.INFO, "row color written",
            color=color, row_ref=self._row_ref_str(row_ref),
        )

    def verify_cell(
        self, row_ref: SheetRowRef, column: str, expected_value: str
    ) -> bool:
        try:
            actual = self.get_row_values(row_ref).get(column)
        except Exception as exc:
            log_event(
                _logger, logging.WARNING, "cell verification failed",
                column=column, row_ref=self._row_ref_str(row_ref), error=str(exc),
            )
            return False
        if actual != expected_value:
            log_event(
                _logger, logging.WARNING, "cell verification failed",
                column=column, row_ref=self._row_ref_str(row_ref),
            )
            return False
        return True

    # -- find_by_* — scan the OGR master register (DB-DESIGN.md §A.1) ----
    #
    # Not called by any engine code yet (grep-confirmed 2026-09-27) — the
    # workflow engine always already holds a SheetRowRef by the time it
    # needs one. These exist to satisfy the StudentSheetRepository
    # Protocol and for future student-discovery use.
    #
    # Assumption, flagged rather than guessed past silently (RULEBOOK.md
    # K1): Student.student_id has no source column in any of the three
    # sheets — it's this app's own internal case key (used to index the
    # local, append-only pen_case_events table, DB-DESIGN.md §B.1) and
    # must stay stable for the same student across every run. OGR's
    # AADHAR column is used as that stable key here (Aadhaar is already
    # the documented duplicate-matching signal, spec §6) when present;
    # a row with no Aadhaar on file falls back to a row-position key,
    # which is NOT stable if that row is later reordered/deleted in the
    # spreadsheet — logged as a warning so this can be revisited before
    # any real workflow depends on it.
    def _ogr_tab_titles(self, spreadsheet_id: str) -> list[str]:
        meta = self._client().spreadsheets().get(
            spreadsheetId=spreadsheet_id, fields="sheets.properties.title"
        ).execute()
        return [s["properties"]["title"] for s in meta.get("sheets", [])]

    def _iter_ogr_rows(self):
        spreadsheet_id = self._resolve_spreadsheet_id("OGR")
        for tab in self._ogr_tab_titles(spreadsheet_id):
            meta = self._tab_meta(spreadsheet_id, tab)
            if not meta.headers:
                continue
            last_col = _col_letter(max(meta.headers.values()))
            result = self._client().spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"'{tab}'!A2:{last_col}"
            ).execute()
            for offset, raw_row in enumerate(result.get("values", [])):
                row_ref = SheetRowRef("OGR", tab, offset + 2)
                values = {
                    name: (raw_row[idx] if idx < len(raw_row) else "")
                    for name, idx in meta.headers.items()
                }
                yield row_ref, values

    def _student_from_ogr_row(
        self, row_ref: SheetRowRef, values: dict[str, str]
    ) -> Student:
        aadhaar = values.get("AADHAR", "").strip()
        if aadhaar:
            student_id = f"aadhar:{aadhaar}"
        else:
            student_id = f"ogr-row:{row_ref.tab}:{row_ref.row_number}"
            log_event(
                _logger, logging.WARNING,
                "student identity fell back to row position (no Aadhaar on "
                "OGR row) - unstable if the row is later reordered/deleted",
                row_ref=self._row_ref_str(row_ref),
            )
        return Student(
            student_id=student_id,
            name=values.get("NAME", ""),
            class_name=values.get("STD", ""),
            aadhaar=aadhaar or None,
            uid_udise=values.get("UID") or None,
            pen=values.get("PEN") or None,
            ogr_row=row_ref,
        )

    def find_by_name(
        self, name: str, class_name: str | None = None
    ) -> list[Student]:
        target = name.strip().lower()
        matches = []
        for row_ref, values in self._iter_ogr_rows():
            if values.get("NAME", "").strip().lower() != target:
                continue
            if class_name is not None and values.get("STD", "") != class_name:
                continue
            matches.append(self._student_from_ogr_row(row_ref, values))
        return matches

    def find_by_uid(self, uid: str) -> Student | None:
        for row_ref, values in self._iter_ogr_rows():
            if values.get("UID", "").strip() == uid.strip():
                return self._student_from_ogr_row(row_ref, values)
        return None

    def find_by_pen(self, pen: str) -> Student | None:
        for row_ref, values in self._iter_ogr_rows():
            if values.get("PEN", "").strip() == pen.strip():
                return self._student_from_ogr_row(row_ref, values)
        return None
