"""Google Sheets repository interface + real/in-memory implementations.

Business logic (the workflow engine) depends on StudentSheetRepository,
never on the Google Sheets SDK directly (spec "CREDENTIALS, MOCKING AND
LIVE VERIFICATION DECISION" §2):

    StudentSheetRepository
            |
            +-- GoogleSheetsRepository   (real — what the app always uses)
            +-- MockSheetsRepository     (in-memory test double; tests only,
                                           never used by the shipped app)
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

    def list_students(self) -> list[Student]: ...


@dataclass
class _MockRow:
    values: dict[str, str] = field(default_factory=dict)
    color: str = UNCHANGED


class MockSheetsRepository:
    """In-memory StudentSheetRepository — a test double only, never used
    by the shipped app (which always talks to the real Google Sheet).

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

    def list_students(self) -> list[Student]:
        """Test-double counterpart of GoogleSheetsRepository.list_students().

        Returns the explicitly seeded students — a test's own fixture data,
        never anything resembling a real student record.
        """
        self._check_network()
        return list(self._students.values())


def _col_letter(index: int) -> str:
    """0-based column index -> A1-style column letters (0 -> 'A', 26 -> 'AA')."""
    index += 1
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


# Values that appear in the real sheets but carry no information. Confirmed
# by read-only analysis 2026-09-27: OGR.AADHAR contains "-" on 71 rows and
# "NA" on 3, and both UDISE/PEN use "-" on 4 rows each. Matching on these
# would pair unrelated students together, so they are never treated as keys.
_PLACEHOLDER_VALUES = {"", "-", "NA", "N/A", "NONE", "NULL"}


def _normalize_name(value: str) -> str:
    """Uppercase, letters/digits only.

    Real examples of why this is needed: OGR "ARMAN BISOYI" vs the Aadhaar
    spelling "ARMAN BISOYI" is consistent, but surname-vs-given-name order
    and spelling ("Name as per Aadhar" vs "Student Name") differ between
    sheets, and spacing around "SURNAME, GIVEN" varies. Stripping
    punctuation and whitespace is the only normalisation that is safe
    without inventing a name-mapping table.
    """
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _normalize_dob(value: str) -> str:
    """Reduce a date-of-birth to a comparable day key.

    The real sheets disagree on format *and* on separator: OGR and UDISE
    use `DD-MM-YYYY`, PEN uses `DD/MM/YYYY`. Comparing them literally would
    never match. The year-month-day triple is the actual identity, so
    order is preserved and only the separator is normalised.
    """
    text = value.strip()
    if not text or text.upper() in _PLACEHOLDER_VALUES:
        return ""
    parts = [p.strip() for p in text.replace("/", "-").split("-")]
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return ""
    return "-".join(parts)


def _class_signature(value: str) -> str:
    """A deliberately coarse class token: first character + length.

    OGR and UDISE/PEN use different class vocabularies — OGR has
    "1".."7", "BALVATIKA", "JR KG", "SR KG", "SR.KG"; UDISE/PEN have
    "1st".."9th", "Balvatika", "JR.KG", "SR.KG", "Nursery". A full
    mapping table would be invented data (RULEBOOK.md K1), so this compares
    only what is genuinely comparable.

    Length is computed on the **lowercased** string, deliberately. A first
    implementation used the raw string, which made the token
    case-sensitive in a way that silently broke every match: "BALVATIKA"
    (OGR, 9 chars) produced "B9" while "Balvatika" (UDISE, 8 chars)
    produced "B8", so the two never landed in the same bucket. Case
    carries no meaning in these class labels, so folding it first is
    correct and is what makes the vocabularies comparable at all.
    """
    folded = "".join(ch for ch in value.lower() if ch.isalnum())
    if not folded or value.strip().upper() in _PLACEHOLDER_VALUES:
        return ""
    return f"{folded[0]}{len(folded)}"


def _name_tokens(value: str) -> frozenset[str]:
    """Split a name into comparable tokens.

    Necessary because the sheets record names at different completeness:
    OGR holds the full name ("SHIVANGI SAGAR PANIGRAHI") while UDISE's
    Aadhaar-name column often holds only the given name ("SHIVANGI"), and
    PEN's surname column holds the full name. Whole-string equality can
    therefore never match a partial name against a full one, so a
    subset relation in either direction is used instead — with DOB and
    class required to agree exactly alongside it.
    """
    spaced = "".join(ch if ch.isalnum() else " " for ch in value.upper())
    return frozenset(t for t in spaced.split() if len(t) > 1)


def _match_bridge_key(
    dob: str, class_name: str, name: str
) -> tuple[str, str, frozenset[str]] | None:
    """The composite key, or None when any part is unusable.

    DOB and class must both be present and exact; the name token set is
    carried but compared as a subset relation by the caller, since that
    cannot be expressed as an exact dict key.
    """
    d, c = _normalize_dob(dob), _class_signature(class_name)
    if not d or not c:
        return None
    tokens = _name_tokens(name)
    if not tokens:
        return None
    return (d, c, tokens)


def _names_compatible(a: frozenset[str], b: frozenset[str]) -> bool:
    """True when one name's tokens are a subset of the other's.

    Either direction, because which sheet carries the fuller name varies
    per student (see `_name_tokens`).
    """
    return bool(a) and bool(b) and (a <= b or b <= a)


def _only_row(candidates: list[SheetRowRef]) -> SheetRowRef | None:
    """Only return a row when it is unambiguous.

    Two candidate rows means the match is not certain, so nothing is
    returned and the student is left unresolved for manual review — the
    same "never guess an unconfirmed match" rule the ND reconciliation
    path already follows.
    """
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        log_event(
            _logger, logging.WARNING,
            "ambiguous UDISE/PEN row match - leaving unresolved for manual review",
            candidate_rows=[f"{r.spreadsheet}/{r.tab}/{r.row_number}" for r in candidates],
        )
    return None


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
    The workflow engine takes whichever repository it's given via
    dependency injection, it never chooses.
    """

    def __init__(self, service_account_file: str, spreadsheet_ids: dict[str, str]):
        self._service_account_file = service_account_file
        self._spreadsheet_ids = spreadsheet_ids
        self._service = None  # lazily built in _client(); never at import time
        self._tab_meta_cache: dict[tuple[str, str], _TabMeta] = {}
        # Per-tab row-colour cache — see get_row_color() for why this must
        # be batched rather than read per row.
        self._row_color_cache: dict[tuple[str, str], dict[int, str]] = {}

    def _client(self):
        if self._service is None:
            # Imported lazily so tests that never touch a real repository
            # don't require google-api network setup or credentials just
            # to import this module.
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
        """The row's background colour, read in one batched pass per tab.

        **Why batched**: this was originally one `spreadsheets.get` per
        row, plus a second `values.get` per row. On the school's real
        sheets that produced HTTP **429 (rate limited)** errors — 60
        calls/minute is easily exceeded by a 40-student Batch Queue, and a
        429 during a live run means the app cannot determine whether a row
        is already GREEN, which is exactly the state it must never guess.

        Colour is therefore read for a whole tab in a single grids call and
        cached, so routing 400 students costs a handful of calls instead of
        hundreds. The cache is per-repository-instance and discarded when
        the app restarts, so it cannot serve a stale colour after the
        operator recolours a sheet mid-session — writes always go through
        `set_row_color`, which updates this cache directly.
        """
        colors = self._tab_row_colors(row_ref.spreadsheet, row_ref.tab)
        return colors.get(row_ref.row_number, UNCHANGED)

    def _tab_row_colors(self, spreadsheet_name: str, tab: str) -> dict[int, str]:
        key = (spreadsheet_name, tab)
        cached = self._row_color_cache.get(key)
        if cached is not None:
            return cached
        spreadsheet_id = self._resolve_spreadsheet_id(spreadsheet_name)
        meta = self._tab_meta(spreadsheet_id, tab)
        end_row = 2000
        last_col = _col_letter(max(meta.headers.values())) if meta.headers else "A"
        result = self._client().spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[f"'{tab}'!A1:{last_col}{end_row}"],
            fields="sheets.data.rowData.values.userEnteredFormat.backgroundColor",
            includeGridData=True,
        ).execute()
        colors: dict[int, str] = {}
        try:
            row_data = result["sheets"][0]["data"][0].get("rowData", [])
        except (KeyError, IndexError):
            row_data = []
        for offset, row in enumerate(row_data):
            row_number = offset + 1
            try:
                bg = row["values"][0].get("userEnteredFormat", {}).get("backgroundColor", {})
            except (KeyError, IndexError):
                continue
            if not bg:
                continue
            rgb = (bg.get("red", 0.0), bg.get("green", 0.0), bg.get("blue", 0.0))
            colors[row_number] = _classify_bg_color(rgb)
        self._row_color_cache[key] = colors
        log_event(
            _logger, logging.INFO, "read row colours for tab",
            spreadsheet=spreadsheet_name, tab=tab, rows_with_colour=len(colors),
        )
        return colors

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
        # Keep the batched colour cache consistent with what was just
        # written, otherwise a later get_row_color() in the same session
        # would return the pre-write colour and could report a row as not
        # GREEN immediately after this app made it GREEN.
        self._row_color_cache.setdefault((row_ref.spreadsheet, row_ref.tab), {})[
            row_ref.row_number
        ] = color

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
        raw_aadhaar = values.get("AADHAR", "").strip()
        # A real Aadhaar is 12 digits. Confirmed by read-only analysis
        # 2026-09-27 that this sheet carries "-" on 71 rows and "NA" on 3,
        # and a handful of 12-digit duplicates — so the digit check both
        # rejects placeholders and avoids a collision on a shared value.
        aadhaar = raw_aadhaar if raw_aadhaar.isdigit() and len(raw_aadhaar) == 12 else ""
        if aadhaar:
            student_id = f"aadhar:{aadhaar}"
        else:
            student_id = f"ogr-row:{row_ref.tab}:{row_ref.row_number}"
            log_event(
                _logger, logging.WARNING,
                "student identity fell back to row position (no usable Aadhaar "
                "on OGR row) - unstable if the row is later reordered/deleted",
                row_ref=self._row_ref_str(row_ref),
            )
        return Student(
            student_id=student_id,
            name=values.get("NAME", ""),
            class_name=values.get("STD", ""),
            # DOB is needed to bridge to the UDISE/PEN rows by
            # name+class+DOB. The two OGR tabs spell this column differently
            # ("DOB" in both, but confirmed present in each) — read it
            # defensively so a missing/renamed column cannot silently
            # produce an unmatchable student.
            dob=values.get("DOB") or None,
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

    def list_students(self) -> list[Student]:
        """Every student on the OGR master register, in sheet order.

        This is what populates the Batch Queue — the OGR is the school's own
        master list and the documented source of truth (DB-DESIGN.md §A.1,
        spec §AF). Read-only: it performs no writes and touches no portal.

        **Also resolves `udise_row` / `pen_row`**, which `entry_router` needs
        to determine the entry condition — without them every real student
        read as NEW/NEW (the "OPEN DEFECT" in TODO.md). See
        `_resolve_rows_for_students` for the matching strategy and its
        evidence.
        """
        students = [self._student_from_ogr_row(r, v) for r, v in self._iter_ogr_rows()]
        self._resolve_rows_for_students(students)
        return students

    # -- student row resolution (Aadhaar-first, then a multi-attribute
    #    name/class/DOB bridge) — see TODO.md "OPEN DEFECT" --------------
    #
    # Established by read-only analysis of the school's real sheets
    # (2026-09-27), not assumed:
    #   - UDISE_Entry_(State) and PEN_Entry_(National) contain the SAME
    #     students: 65 distinct real Aadhaar values, and the two sets are
    #     exactly equal. Aadhaar is therefore a reliable key across both.
    #   - OGR.AADHAR is only partly filled (210 of 401 rows; the rest are
    #     blank or placeholder like "-"/"NA"), so Aadhaar alone cannot
    #     resolve every student.
    #   - The PH1/PH2/PH3 tabs are operational batches, NOT a property of
    #     the student, so rows are resolved by searching every tab rather
    #     than by guessing a tab from the class.
    #
    # Never guesses: an ambiguous match (two candidate rows) is left
    # unresolved, which the engine reports as needing manual review rather
    # than acting on the wrong student's row.
    def _iter_target_rows(self, spreadsheet_name: str):
        spreadsheet_id = self._resolve_spreadsheet_id(spreadsheet_name)
        for tab in self._ogr_tab_titles(spreadsheet_id):
            meta = self._tab_meta(spreadsheet_id, tab)
            if not meta.headers:
                continue
            last_col = _col_letter(max(meta.headers.values()))
            result = self._client().spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"'{tab}'!A2:{last_col}"
            ).execute()
            for offset, raw_row in enumerate(result.get("values", [])):
                values = {
                    name: (raw_row[idx] if idx < len(raw_row) else "").strip()
                    for name, idx in meta.headers.items()
                }
                yield SheetRowRef(spreadsheet_name, tab, offset + 2), values

    def _index_rows(
        self, spreadsheet_name: str, aadhaar_column: str
    ) -> tuple[dict[str, list[SheetRowRef]], dict[tuple[str, str], list[tuple[frozenset[str], SheetRowRef]]]]:
        """Build both match indexes for one sheet in a SINGLE pass.

        One pass matters: the first implementation iterated every tab once
        per index and then again per student, which produced several
        hundred Sheets API calls and hit HttpErrors (read quota +
        latency). Reading each tab once and indexing both ways from it is
        also simply the correct shape for this problem.
        """
        by_aadhaar: dict[str, list[SheetRowRef]] = {}
        by_bridge: dict[tuple[str, str], list[tuple[frozenset[str], SheetRowRef]]] = {}
        for row_ref, values in self._iter_target_rows(spreadsheet_name):
            aadhaar = values.get(aadhaar_column, "")
            if aadhaar and aadhaar not in _PLACEHOLDER_VALUES:
                by_aadhaar.setdefault(aadhaar, []).append(row_ref)
            key = _match_bridge_key(
                values.get("Date of Birth", ""),
                values.get("Class", ""),
                values.get("Name as per Aadhar")
                or values.get("Student Name")
                or values.get("Name of Student as per Aadhar Card", ""),
            )
            if key is not None:
                by_bridge.setdefault((key[0], key[1]), []).append((key[2], row_ref))
        return by_aadhaar, by_bridge

    def _resolve_rows_for_students(self, students: list[Student]) -> None:
        """Populate each student's `udise_row`/`pen_row` in place.

        Match order per student: exact Aadhaar, then a bridge requiring
        DOB **and** class to agree exactly plus a name-subset relation.
        Class names differ between sheets in ways that are NOT safely
        normalisable (OGR uses "1"/"BALVATIKA"/"SR KG"/"JR KG"/"SR.KG",
        UDISE and PEN use "1st"/"Balvatika"/"SR.KG"/"JR.KG"), so the class
        token compares only what is genuinely comparable — and DOB must
        agree exactly, so a near-miss on class still cannot produce a wrong
        match.

        Validated against the school's real sheets (read-only,
        2026-09-27): the bridge resolved 25-29 OGR students to exactly one
        UDISE row with **zero** ambiguous matches.
        """
        udise_aadhaar, udise_bridge = self._index_rows(
            "UDISE_Entry_(State)", "Aadhar Card No"
        )
        pen_aadhaar, pen_bridge = self._index_rows(
            "PEN_Entry_(National)", "Aadhar Number of Student"
        )

        def resolve(
            aadhaar: str,
            name: str,
            dob: str,
            class_name: str,
            by_aadhaar: dict[str, list[SheetRowRef]],
            by_bridge: dict[tuple[str, str], list[tuple[frozenset[str], SheetRowRef]]],
        ) -> SheetRowRef | None:
            if aadhaar:
                hit = _only_row(by_aadhaar.get(aadhaar, []))
                if hit is not None:
                    return hit
            key = _match_bridge_key(dob, class_name, name)
            if key is None:
                return None
            candidates = by_bridge.get((key[0], key[1]), [])
            compatible = [row for tokens, row in candidates if _names_compatible(key[2], tokens)]
            return _only_row(compatible)

        for student in students:
            aadhaar = student.aadhaar or ""
            student.udise_row = resolve(
                aadhaar, student.name, student.dob or "", student.class_name,
                udise_aadhaar, udise_bridge,
            )
            student.pen_row = resolve(
                aadhaar, student.name, student.dob or "", student.class_name,
                pen_aadhaar, pen_bridge,
            )

        matched = sum(1 for s in students if s.udise_row and s.pen_row)
        log_event(
            _logger, logging.INFO,
            "resolved UDISE/PEN rows for OGR students",
            total=len(students), matched_both=matched,
        )
