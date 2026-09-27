r"""L2 — real Google Sheets, READ-ONLY.

Reads the school's three real spreadsheets and reports what it found. Makes
**no writes of any kind** — no cell write, no colour change. Safe to run.

    .venv\Scripts\python.exe tests\live\L2_sheets_readonly.py

This is the cheapest real evidence available: it retires the largest
untested surface (the Gujarat/spreadsheet half) without touching a portal
or mutating a register.
"""

from __future__ import annotations

from _live_common import banner, require_live_settings, show_config_summary

from src.sheets.repository import GoogleSheetsRepository, _PLACEHOLDER_VALUES


def main() -> int:
    settings = require_live_settings()
    show_config_summary(settings)

    repo = GoogleSheetsRepository(
        settings.sheets.service_account_file or "",
        {
            "OGR": settings.sheets.spreadsheet_id_ogr or "",
            "UDISE": settings.sheets.spreadsheet_id_udise or "",
            "PEN": settings.sheets.spreadsheet_id_pen or "",
        },
    )

    banner("L2 step 1 - read every tab of all three real spreadsheets")
    for label, name in (
        ("OGR", "OGR"),
        ("UDISE_Entry_(State)", "UDISE_Entry_(State)"),
        ("PEN_Entry_(National)", "PEN_Entry_(National)"),
    ):
        spreadsheet_id = repo._resolve_spreadsheet_id(name)
        for tab in repo._ogr_tab_titles(spreadsheet_id):
            meta = repo._tab_meta(spreadsheet_id, tab)
            rows = list(repo._iter_target_rows(name)) if name == label else []
            print(f"  {label:24} tab {tab!r:34} columns={len(meta.headers)}")

    banner("L2 step 2 - OGR student list and UDISE/PEN row resolution")
    students = repo.list_students()
    both = [s for s in students if s.udise_row and s.pen_row]
    udise_only = [s for s in students if s.udise_row and not s.pen_row]
    pen_only = [s for s in students if s.pen_row and not s.udise_row]
    neither = [s for s in students if not s.udise_row and not s.pen_row]
    with_aadhaar = sum(1 for s in students if s.aadhaar)
    with_dob = sum(1 for s in students if s.dob)

    print(f"  total students                : {len(students)}")
    print(f"  with a usable Aadhaar         : {with_aadhaar}")
    print(f"  with a usable DOB             : {with_dob}")
    print(f"  resolved to BOTH rows         : {len(both)}")
    print(f"  resolved UDISE row only       : {len(udise_only)}")
    print(f"  resolved PEN row only         : {len(pen_only)}")
    print(f"  no row in either sheet        : {len(neither)}")
    print()
    print("  'no row in either sheet' is expected: those are students who have not")
    print("  yet been entered on that portal. A HIGH number there combined with a low")
    print("  'resolved to BOTH' would mean the matcher is not working.")

    banner("L2 step 3 - entry-condition routing (read-only, no portal access)")
    from collections import Counter

    from src.engine.entry_router import determine_entry_condition

    counts: Counter[str] = Counter()
    errors: list[str] = []
    for student in students:
        try:
            counts[determine_entry_condition(repo, student).condition.value] += 1
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {str(exc)[:120]}")
    for condition, count in counts.most_common():
        print(f"  {condition:20} {count}")
    print(f"  errors: {len(errors)}")
    for message in errors[:5]:
        print(f"    {message}")

    banner("L2 step 4 - row colour reads (the GREEN detection the engine relies on)")
    coloured = 0
    unreadable = 0
    for student in students:
        if not student.udise_row:
            continue
        try:
            if repo.get_row_color(student.udise_row) != "UNCHANGED":
                coloured += 1
        except Exception as exc:
            unreadable += 1
            print(f"    colour read failed: {type(exc).__name__}: {str(exc)[:100]}")
    print(f"  UDISE rows with a recognised colour : {coloured}")
    print(f"  colour reads that failed            : {unreadable}")
    if unreadable:
        print("  -> non-zero means HTTP 429 rate limiting; the batched colour read")
        print("     should prevent this. Report it rather than retrying in a loop.")

    banner("L2 result")
    if errors or unreadable:
        print("FAILED - see the errors above. Nothing was written to any sheet.")
        return 1
    print("PASSED - all three real spreadsheets read successfully, read-only.")
    print("No cell, colour, portal or database record was modified by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
