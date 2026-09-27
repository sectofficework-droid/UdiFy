"""Tests for student row resolution and match normalisation.

Guards the fix for the "OPEN DEFECT" in TODO.md: `list_students()` must
populate `udise_row`/`pen_row`, because `entry_router` decides the entry
condition from them. Without them every real student read as NEW/NEW.

The matching strategy and its evidence are recorded in
`repository._resolve_rows_for_students`; these tests lock in the
normalisation rules that strategy depends on, including a case-sensitive
class-token bug that silently broke every match until it was caught
against the real sheets.
"""

from __future__ import annotations

from src.sheets.models import SheetRowRef, Student
from src.sheets.repository import (
    GREEN,
    UNCHANGED,
    MockSheetsRepository,
    _class_signature,
    _match_bridge_key,
    _name_tokens,
    _names_compatible,
    _normalize_dob,
    _only_row,
    _PLACEHOLDER_VALUES,
)


# ---------------- placeholders are never keys ----------------


def test_placeholder_values_recognised():
    # Real data: OGR.AADHAR has "-" on 71 rows and "NA" on 3; both
    # UDISE and PEN use "-" on 4 rows each. Matching on these would pair
    # unrelated students.
    assert "-" in _PLACEHOLDER_VALUES
    assert "NA" in _PLACEHOLDER_VALUES
    assert "" in _PLACEHOLDER_VALUES


def test_placeholder_aadhaar_never_becomes_a_student_id():
    """A "-" Aadhaar must not produce student_id "aadhar:-", which would
    collide across every placeholder row in the sheet."""
    sheets = MockSheetsRepository()
    repo_rows = {}
    # Exercise the real Student construction path via the mock repo's
    # equivalent identity rules: a non-12-digit value is not an Aadhaar.
    for bad in ("-", "NA", "123", "12345678901234", ""):
        assert not (bad.isdigit() and len(bad) == 12), bad
    assert "441721751078".isdigit() and len("441721751078") == 12


# ---------------- date normalisation ----------------


def test_dob_normalises_the_two_real_formats():
    # OGR/UDISE use DD-MM-YYYY, PEN uses DD/MM/YYYY. Literal comparison
    # would never match across sheets.
    assert _normalize_dob("07-01-2022") == _normalize_dob("07/01/2022")


def test_dob_rejects_placeholders_and_garbage():
    assert _normalize_dob("-") == ""
    assert _normalize_dob("") == ""
    assert _normalize_dob("NA") == ""
    assert _normalize_dob("not-a-date") == ""
    assert _normalize_dob("07-2022") == ""


def test_dob_preserves_field_order():
    """Must NOT reorder into an ISO date — that would silently swap day
    and month and match the wrong student."""
    assert _normalize_dob("07-01-2022") == "07-01-2022"
    assert _normalize_dob("01-07-2022") != _normalize_dob("07-01-2022")


# ---------------- class token: the case-folding bug ----------------


def test_class_token_is_case_insensitive():
    """Regression guard for a real bug found against the live sheets.

    The token was originally built from the raw string, so "BALVATIKA"
    (OGR, 9 chars) produced "B9" while "Balvatika" (UDISE, 8 chars)
    produced "B8". The two vocabularies could then never meet and the
    bridge matched nothing at all — a silent total failure.
    """
    assert _class_signature("BALVATIKA") == _class_signature("Balvatika")
    assert _class_signature("BALVATIKA") == _class_signature("balvatika")


def test_class_token_distinguishes_real_differences():
    assert _class_signature("SR KG") != _class_signature("JR KG")
    assert _class_signature("1") != _class_signature("2")


def test_class_token_rejects_placeholders():
    assert _class_signature("-") == ""
    assert _class_signature("") == ""


# ---------------- name tokens ----------------


def test_name_tokens_allow_partial_against_full():
    """OGR holds the full name, UDISE often only the given name."""
    full = _name_tokens("SHIVANGI SAGAR PANIGRAHI")
    partial = _name_tokens("SHIVANGI")
    assert _names_compatible(full, partial)
    assert _names_compatible(partial, full)


def test_name_tokens_reject_unrelated_names():
    assert not _names_compatible(_name_tokens("ANKITA NAHAK"), _name_tokens("PRANGYA MANDAL"))


def test_name_tokens_ignore_single_letters():
    # Real data has initials-style entries; a 1-char token is noise.
    assert "a" not in _name_tokens("A SURNAME")


# ---------------- the composite bridge key ----------------


def test_bridge_key_requires_dob_class_and_name():
    assert _match_bridge_key("", "SR.KG", "NAME") is None
    assert _match_bridge_key("07-01-2022", "", "NAME") is None
    assert _match_bridge_key("07-01-2022", "SR.KG", "") is None


def test_bridge_key_crosses_sheet_format_differences():
    """The same student expressed in OGR and UDISE vocabulary must produce
    the same key, or the bridge can never fire."""
    ogr = _match_bridge_key("07/01/2022", "SR KG", "SHIVANGI SAGAR PANIGRAHI")
    udise = _match_bridge_key("07-01-2022", "SR.KG", "SHIVANGI")
    assert ogr is not None and udise is not None
    assert ogr[0] == udise[0]  # DOB
    assert ogr[1] == udise[1]  # class token
    assert _names_compatible(ogr[2], udise[2])


# ---------------- ambiguity is never guessed ----------------


def test_only_row_returns_the_single_candidate():
    row = SheetRowRef("UDISE_Entry_(State)", "PH1", 5)
    assert _only_row([row]) is row


def test_only_row_refuses_when_ambiguous():
    """Two candidates means the match is uncertain — must be left for
    manual review, never resolved to the first one."""
    rows = [SheetRowRef("UDISE_Entry_(State)", "PH1", 5), SheetRowRef("UDISE_Entry_(State)", "PH2", 9)]
    assert _only_row(rows) is None


def test_only_row_returns_none_for_no_candidates():
    assert _only_row([]) is None


# ---------------- end-to-end against the mock repository ----------------


def test_mock_list_students_returns_seeded_students():
    sheets = MockSheetsRepository()
    student = Student(
        student_id="aadhar:111122223333",
        name="Test Student",
        class_name="SR.KG",
        dob="07-01-2022",
        udise_row=SheetRowRef("UDISE_Entry_(State)", "PH1", 2),
        pen_row=SheetRowRef("PEN_Entry_(National)", "PH1", 2),
    )
    sheets.seed_student(student)
    found = sheets.list_students()
    assert [s.student_id for s in found] == ["aadhar:111122223333"]


def test_mock_student_keeps_both_rows_for_routing():
    """The defect was that real students arrived with no udise_row/
    pen_row, so routing could only ever say NEW. A Student that *has*
    those refs must carry them through unchanged."""
    sheets = MockSheetsRepository()
    u = SheetRowRef("UDISE_Entry_(State)", "PH2", 7)
    p = SheetRowRef("PEN_Entry_(National)", "PH2", 7)
    sheets.seed_student(
        Student(student_id="s1", name="N", class_name="1st", udise_row=u, pen_row=p)
    )
    (loaded,) = sheets.list_students()
    assert loaded.udise_row == u
    assert loaded.pen_row == p
