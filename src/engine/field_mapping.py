"""Sheet-row -> portal-form field mapping.

Deliberately a separate, explicit, overridable layer (spec §104/§167/§269
"field mapping layer") — never inline guesses baked into the engine or
adapters. Where the spreadsheet's actual columns don't map 1:1 onto a
portal form's fields, that gap is called out in a comment, not silently
resolved by invention (RULEBOOK.md K1: never assume from a name/layout).

Known gap, flagged rather than guessed past: the UDISE_Entry_(State)
sheet has a single "Birth City" column (spec §5.2), but the Gujarat
portal's manual birth-entry route asks for Birth State/District/Taluka/
City/Village as five separate fields (spec §18). This mapping defaults
Taluka and Village to the sheet's Birth City value as a documented,
visible assumption — not a spec-confirmed fact — until live-DOM
verification either confirms it or reveals separate source columns.
"""

from __future__ import annotations

from src.diagnostics.logging_setup import get_logger, log_event
from src.portals.udise_gujarat.adapter import CtsDetails, ManualBirthDetails
from src.portals.udise_plus.adapter import NewStudentInit

_logger = get_logger("engine.field_mapping")


def udise_row_to_birth_details(row: dict[str, str]) -> ManualBirthDetails:
    """UDISE_Entry_(State) row -> ManualBirthDetails for the manual route.

    row keys are the sheet's exact column headers (DB-DESIGN.md §A.2).
    """
    birth_city = row.get("Birth City", "")
    log_event(
        _logger, 20, "mapping UDISE row to birth details",
        assumption="Birth Taluka/Village default to Birth City (unconfirmed)",
    )
    return ManualBirthDetails(
        birth_state=row.get("Birth State", ""),
        birth_district=row.get("Birth District", ""),
        birth_taluka=birth_city,  # assumption — see module docstring
        birth_city_or_place=birth_city,
        birth_village=birth_city,  # assumption — see module docstring
        year=row.get("Birth Year", ""),
        month=row.get("Birth Month", ""),
        date=row.get("Birth Date", ""),
        brn_present=bool(row.get("Birth Cert Reg No", "")),
        brn_no=row.get("Birth Cert Reg No") or None,
    )


def udise_row_to_cts_details(row: dict[str, str]) -> CtsDetails:
    """UDISE_Entry_(State) row -> CtsDetails (spec §20's CTS fields).

    Disability fields are not present in the confirmed 29-column UDISE
    sheet header list (DB-DESIGN.md §A.2) — defaults to not-disabled
    rather than inventing a column that isn't there.
    """
    return CtsDetails(
        student_name=row.get("Student Name", ""),
        father_name=row.get("Father's Name", ""),
        mother_name=row.get("Mother's Name", ""),
        surname=row.get("Surname", ""),
        dob=row.get("Date of Birth", ""),
        disabled=False,
        disability_type=None,
    )


def udise_row_to_personal_tab_fields(row: dict[str, str]) -> dict[str, str]:
    """UDISE_Entry_(State) row -> {label: value} for the Personal tab.

    Only the fields this project has confirmed labels for (spec §23-24)
    are mapped — Scholarship & Facility / Health & CWSN stay out of this
    function entirely (needs-live-verification, UI-SPEC.md §B.5), rather
    than guessing labels for them.
    """
    return {
        "Mother Tongue": row.get("Mother Tongue", ""),
    }


def pen_row_to_new_student_init(
    row: dict[str, str], *, class_name: str, section: str
) -> NewStudentInit:
    """PEN_Entry_(National) row -> NewStudentInit (spec §37)."""
    return NewStudentInit(
        student_name=_full_name(row), class_name=class_name, section=section
    )


def pen_row_to_general_profile_fields(row: dict[str, str]) -> dict[str, str]:
    """PEN_Entry_(National) row -> {label: value} for General Profile
    (spec §41-42's confirmed fields, subset with confirmed labels)."""
    return {
        "Mother Tongue of Student": row.get("Mother Tongue", ""),
    }


def pen_row_to_enrolment_profile_fields(row: dict[str, str]) -> dict[str, str]:
    """spec §46's confirmed fields, subset with confirmed labels."""
    return {
        "Admission Number in Present School": row.get(
            "Admission Number in Present School (GR No)", ""
        ),
    }


def pen_row_to_facility_profile_fields(row: dict[str, str]) -> dict[str, str]:
    """spec §50's confirmed fields."""
    return {
        "Student's Height (in CMS)": row.get("Height (cm)", ""),
        "Student's Weight (in KGS)": row.get("Weight (kg)", ""),
    }


def _full_name(row: dict[str, str]) -> str:
    # PEN sheet has no single "Student Name" column (DB-DESIGN.md §A.3) —
    # it has Student Father Surname / Name of Student as per Aadhar Card.
    # Prefer the Aadhaar-matching name since that's what the portal cross-
    # verifies against (spec §40).
    return row.get("Name of Student as per Aadhar Card", "")
