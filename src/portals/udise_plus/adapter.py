"""National UDISE+ (Student Database Management System) portal adapter.

Implements the confirmed New PEN Entry workflow (spec §34-53, §164, §Y)
and the confirmed PEN Import — Other School ACTIVE workflow (spec's
"PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW" section,
DB-DESIGN.md §C.3a). The successful/Dropbox PEN Import outcome is NOT
implemented here — it remains `COMING_SOON` (UI-SPEC.md §B.5); do not
infer it from this adapter's methods (the spec explicitly warns against
this — that section's own §19/§27).

Same selector strategy and verification discipline as
src/portals/udise_gujarat/adapter.py: role/label/exact-text locators,
`expect(...).to_be_visible()` for polling, never `Locator.is_visible()`
alone for a state that might take a moment to appear.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.diagnostics.logging_setup import get_logger, log_event
from src.portals.base import (
    AutomationPausedForUser,
    ConsequentialActionUnverifiedError,
    ci_exact,
)

_logger = get_logger("portals.national_udise")

DEFAULT_TIMEOUT_MS = 10_000

AADHAAR_ALREADY_REGISTERED_TEXT = "AADHAAR number is already registered with some other student"
INITIALIZATION_SUCCESS_TEXT = "The Student has been initialised/Saved Successfully."
PROFILE_COMPLETE_TEXT = "Data completion is complete."
RELEASE_REQUEST_SUCCESS_TEXT = "Release Request successfully generated"

# Spec "HOW TO VIEW SENT REQUEST" §3 — the only confirmed raw status; any
# other observed wording must route to manual review, never be guessed.
_KNOWN_RELEASE_REQUEST_STATUSES = {
    "Pending at Destination": "PENDING_AT_DESTINATION",
}


def normalize_release_request_status(raw_status: str) -> str:
    """Never silently map an unrecognized status (spec §3)."""
    return _KNOWN_RELEASE_REQUEST_STATUSES.get(raw_status, "UNKNOWN_PORTAL_STATUS")


@dataclass(frozen=True)
class NewStudentInit:
    """Spec §37 — fields needed to initialize a new National UDISE+ profile."""

    student_name: str
    class_name: str
    section: str


@dataclass(frozen=True)
class TrackByDetailsResult:
    """Spec §8 — what Track By Details returns for an existing student."""

    student_pen: str
    student_name: str
    source_school_udise: str
    source_school_name: str
    student_class: str | None = None
    student_section: str | None = None


@dataclass(frozen=True)
class GlobalSearchResult:
    """Spec §12-13 — Global Student Search by PEN result."""

    student_name: str
    pen: str
    student_status: str  # e.g. "ACTIVE" — spec §13's decisive field
    source_school_name: str
    source_school_udise: str


@dataclass(frozen=True)
class StudentBasicDetails:
    """Spec step 3 — Student Basic Details (as per School record/OGR),
    returned by Get Details. `pen`/`dob` are the caller's own input
    values, not re-read from the DOM — the confirmation screen re-displays
    them under the same labels used to enter them, and re-querying by
    label would be ambiguous once both are visible together."""

    pen: str
    dob: str
    udise_code: str
    school_name: str
    student_name: str
    gender: str
    student_state_code: str
    mother_name: str
    father_name: str
    aadhaar_no: str
    name_as_per_aadhaar: str
    aadhaar_capture_status: str


@dataclass(frozen=True)
class ReleaseAdmissionDetail:
    """Spec step 4 — Student Admission Detail (destination context)."""

    class_name: str
    section: str
    admission_date: str
    remark: str


@dataclass(frozen=True)
class SentRequestRecord:
    """Spec "HOW TO VIEW SENT REQUEST" §2-3 — one row of the Sent
    Requests table, raw status always preserved alongside the normalized
    value (never collapse the two — spec §3)."""

    request_no: str
    pen: str
    requested_by: str
    requested_to: str
    closed_by: str
    raw_status: str
    normalized_status: str


@dataclass(frozen=True)
class SentRequestStudentSnapshot:
    """Spec §5 — "Student Details (At the time the request was
    generated)"."""

    request_no: str
    pen: str
    student_name: str
    mother_name: str
    dob: str
    father_name: str
    class_name: str


@dataclass(frozen=True)
class NdReconciliationCandidate:
    """spec §165/§260 — one row of an ND-reconciliation name search
    result. `current_pen` is the raw observed value ("NA" or an actual
    11-digit PEN) — this adapter never interprets it, the caller does
    (spec §262: never invent/derive a PEN)."""

    student_name: str
    dob: str
    gender: str
    class_name: str
    current_pen: str


@dataclass(frozen=True)
class HosDetails:
    """Spec §14 — source school's Head of School info (cross-school PII —
    see SECURITY-THREAT-MODEL.md's dedicated threat row for this)."""

    state: str
    district: str
    block: str
    hos_name: str
    hos_contact: str


class NationalUDISEPortalAdapter:
    """Drives the National UDISE+ Student Database Management System."""

    def __init__(self, page: Page, *, timeout_ms: int = DEFAULT_TIMEOUT_MS):
        self.page = page
        self.timeout_ms = timeout_ms

    def login(self, username: str, password: str) -> None:
        self.page.get_by_label("Username").fill(username)
        self.page.get_by_label("Password").fill(password)
        if self._captcha_present():
            log_event(
                _logger, logging.INFO, "CAPTCHA detected on login, pausing for operator",
                portal="NATIONAL_UDISE",
            )
            raise AutomationPausedForUser(
                "CAPTCHA present on National UDISE+ login", checkpoint="login"
            )
        self.page.get_by_role("button", name="Login").click()

    def _captcha_present(self) -> bool:
        try:
            return self.page.get_by_label("Captcha").is_visible(timeout=1000)
        except PlaywrightTimeoutError:
            return False

    # ================= New PEN Entry (spec §37-53, §164, §Y) =================
    def initialize_new_student(self, details: NewStudentInit) -> None:
        """Spec §37/§45 — verifies the exact confirmed success modal text,
        never assumes success from the click alone."""
        p = self.page
        p.get_by_label("Class").select_option(label=details.class_name)
        p.get_by_label("Section").select_option(label=details.section)
        p.get_by_label("Student Name").fill(details.student_name)
        p.get_by_role("button", name="Add New Student").click()
        self._verify_visible(
            p.get_by_text(ci_exact(INITIALIZATION_SUCCESS_TEXT)),
            f"Expected initialization success message: {INITIALIZATION_SUCCESS_TEXT!r}",
        )
        log_event(
            _logger, logging.INFO, "student initialized",
            portal="NATIONAL_UDISE", student_name=details.student_name,
        )

    def go_to_fill_general_profile(self) -> None:
        self.page.get_by_role("button", name="Fill General Profile").click()

    def check_aadhaar_consent_required(self) -> bool:
        """Spec §39/§142/§I: this dialog is a controlled human-intervention
        point — this adapter NEVER clicks "I Agree" itself. Returns True
        if present so the caller can raise AutomationPausedForUser with
        full context (student id, run id) that this adapter doesn't have.
        """
        try:
            return self.page.get_by_text(
                "CONSENT FOR DEMOGRAPHIC AUTHENTICATION", exact=True
            ).is_visible(timeout=1000)
        except PlaywrightTimeoutError:
            return False

    def fill_general_profile(self, fields: dict[str, str]) -> None:
        """Label-driven, generic — same rationale as the Gujarat adapter's
        fill_tab(): General Profile has many confirmed fields (spec §41-42)
        but this stays dict-driven rather than hardcoding each one twice.
        """
        for label, value in fields.items():
            self.page.get_by_label(label).fill(value)

    def proceed_from_general_profile(self) -> None:
        """Clicks Next/Save on General Profile. The caller MUST check
        check_aadhaar_consent_required() immediately after this — the
        consent dialog can appear here (spec §39) and must never be
        auto-dismissed by this adapter."""
        self.page.get_by_role("button", name="Next").click()

    def fill_enrolment_profile(self, fields: dict[str, str]) -> None:
        for label, value in fields.items():
            self.page.get_by_label(label).fill(value)
        self.page.get_by_role("button", name="Next").click()

    def fill_facility_profile(self, fields: dict[str, str]) -> None:
        for label, value in fields.items():
            self.page.get_by_label(label).fill(value)
        self.page.get_by_role("button", name="Next").click()

    def complete_profile_preview(self) -> str:
        """Spec §52 — the strongest confirmed final-completion signal.
        Returns the exact observed text; raises if it never appears."""
        p = self.page
        self._verify_visible(
            p.get_by_text(ci_exact(PROFILE_COMPLETE_TEXT)),
            f"Expected final completion message: {PROFILE_COMPLETE_TEXT!r}",
        )
        p.get_by_role("button", name="Okay").click()
        log_event(_logger, logging.INFO, "PEN profile completed", portal="NATIONAL_UDISE")
        return PROFILE_COMPLETE_TEXT

    # ===== PEN Import — Other School ACTIVE (DB-DESIGN.md §C.3a) =====
    def check_aadhaar_availability(self, aadhaar: str) -> bool:
        """Spec steps 4-6: returns True if the Aadhaar is already
        registered elsewhere (existing-student path) — this is a
        business-routing signal, never a technical error (spec §25/§6)."""
        p = self.page
        p.get_by_label(ci_exact("Check AADHAAR Number Availability")).check()
        p.get_by_label(ci_exact("Aadhaar Number")).fill(aadhaar)
        p.get_by_role("button", name="Go").click()
        try:
            expect(
                p.get_by_text(ci_exact(AADHAAR_ALREADY_REGISTERED_TEXT))
            ).to_be_visible(timeout=self.timeout_ms)
            log_event(
                _logger, logging.INFO, "EXISTING_STUDENT_FOUND_BY_AADHAAR",
                portal="NATIONAL_UDISE", event_code="EXISTING_STUDENT_FOUND_BY_AADHAAR",
            )
            return True
        except AssertionError:
            return False

    def open_track_by_details(self) -> TrackByDetailsResult:
        """Spec steps 7-8: View Details -> Track By Details. Exact screen
        name preserved (spec's own instruction — never generalize it)."""
        p = self.page
        p.get_by_role("button", name="View Details").click()
        self._verify_visible(
            p.get_by_text(ci_exact("Track By Details")),
            "Expected the Track By Details screen",
        )
        return TrackByDetailsResult(
            student_pen=p.get_by_label(ci_exact("Student PEN")).input_value(),
            student_name=p.get_by_label(ci_exact("Student Name")).input_value(),
            source_school_udise=p.get_by_label(ci_exact("UDISE Code")).input_value(),
            source_school_name=p.get_by_label(ci_exact("School Name")).input_value(),
        )

    def global_student_search_by_pen(self, pen: str) -> GlobalSearchResult:
        """Spec steps 11-13: Global Student Search, mode = Student PEN.
        `student_status` is the decisive field (spec §13) — the caller
        must check it explicitly, this adapter never interprets it."""
        p = self.page
        p.get_by_text(ci_exact("Global Student Search")).click()
        p.get_by_label(ci_exact("Student PEN")).check()
        p.get_by_label(ci_exact("PEN")).fill(pen)
        p.get_by_role("button", name=ci_exact("Search")).click()
        self._verify_visible(
            p.get_by_label(ci_exact("Student Status")), "Expected a Global Student Search result"
        )
        return GlobalSearchResult(
            student_name=p.get_by_label(ci_exact("Student Name")).input_value(),
            pen=pen,
            student_status=p.get_by_label(ci_exact("Student Status")).input_value(),
            source_school_name=p.get_by_label(ci_exact("School Details")).input_value(),
            source_school_udise=p.get_by_label(ci_exact("School UDISE")).input_value(),
        )

    def open_hos_details(self) -> HosDetails:
        """Spec step 14 — source school's HOS info. Handle with care: this
        is another school's staff contact info, not this school's (see
        SECURITY-THREAT-MODEL.md's dedicated threat row)."""
        p = self.page
        p.get_by_role("button", name="HOS Details").click()
        self._verify_visible(
            p.get_by_text(ci_exact("HOS Details")), "Expected the HOS Details modal"
        )
        return HosDetails(
            state=p.get_by_label(ci_exact("State")).input_value(),
            district=p.get_by_label(ci_exact("District")).input_value(),
            block=p.get_by_label(ci_exact("Block")).input_value(),
            hos_name=p.get_by_label(ci_exact("Headmaster/Principal")).input_value(),
            hos_contact=p.get_by_label(ci_exact("Contact No.")).input_value(),
        )

    # ===== PEN Request Sent — Student Release Request (DB-DESIGN.md §C.3b) =====
    def get_student_release_details(self, pen: str, dob: str) -> StudentBasicDetails:
        """Spec steps 1-3: Student Release Request Management -> Generate
        Student Release Request Within State -> Enter PEN/DOB -> Get
        Details. The caller must verify the returned identity before
        proceeding (spec Final Authority §E multi-attribute identity)."""
        p = self.page
        p.get_by_text(ci_exact("Student Release Request Management")).click()
        p.get_by_text(ci_exact("Generate Student Release Request Within State")).click()
        p.get_by_label(ci_exact("PEN")).fill(pen)
        p.get_by_label(ci_exact("DOB")).fill(dob)
        p.get_by_role("button", name="Get Details").click()
        self._verify_visible(
            p.get_by_text(ci_exact("Student Basic Details")),
            "Expected Student Basic Details after Get Details",
        )
        return StudentBasicDetails(
            pen=pen,
            dob=dob,
            udise_code=p.get_by_label(ci_exact("UDISE Code")).input_value(),
            school_name=p.get_by_label(ci_exact("School Name")).input_value(),
            student_name=p.get_by_label(ci_exact("Student Name")).input_value(),
            gender=p.get_by_label(ci_exact("Gender")).input_value(),
            student_state_code=p.get_by_label(ci_exact("Student State Code")).input_value(),
            mother_name=p.get_by_label(ci_exact("Mother's Name")).input_value(),
            father_name=p.get_by_label(ci_exact("Father's Name")).input_value(),
            aadhaar_no=p.get_by_label(ci_exact("Aadhaar No.")).input_value(),
            name_as_per_aadhaar=p.get_by_label(ci_exact("Name as per Aadhaar")).input_value(),
            aadhaar_capture_status=p.get_by_label(ci_exact("Aadhaar Capture Status")).input_value(),
        )

    def submit_release_admission_detail(self, admission: ReleaseAdmissionDetail) -> None:
        """Spec step 4 — Student Admission Detail (destination class/
        section/admission date/remark)."""
        p = self.page
        p.get_by_label(ci_exact("Class")).select_option(label=admission.class_name)
        p.get_by_label(ci_exact("Section")).select_option(label=admission.section)
        p.get_by_label(ci_exact("Date of Admission")).fill(admission.admission_date)
        p.get_by_label(ci_exact("Select Remark")).select_option(label=admission.remark)

    def generate_release_request(self) -> str:
        """Spec steps 5-7: Generate Student Release Request -> confirmation
        dialog -> Confirm -> success message -> capture Request No. Never
        treats the click alone as success (Final Authority §D)."""
        p = self.page
        p.get_by_role("button", name="Generate Student Release Request").click()
        self._verify_visible(
            p.get_by_text(ci_exact("Confirm Release Request")),
            "Expected the release-request confirmation dialog",
        )
        p.get_by_role("button", name="Confirm").click()
        self._verify_visible(
            p.get_by_text(ci_exact(RELEASE_REQUEST_SUCCESS_TEXT)),
            f"Expected success message: {RELEASE_REQUEST_SUCCESS_TEXT!r}",
        )
        request_no = p.get_by_label(ci_exact("Request No.")).input_value()
        if not request_no:
            raise ConsequentialActionUnverifiedError(
                "Release request succeeded but no Request No. was captured"
            )
        log_event(
            _logger, logging.INFO, "PEN release request generated",
            portal="NATIONAL_UDISE", request_no=request_no,
        )
        return request_no

    # ===== View Sent Request (DB-DESIGN.md §C.3c) =====
    def open_sent_requests(self) -> None:
        """Spec "HOW TO VIEW SENT REQUEST" §1-2 navigation."""
        p = self.page
        p.get_by_text(ci_exact("Student Release Request Management")).click()
        p.get_by_text(
            "View Student Release Request(s) Within State (Sent)", exact=True
        ).click()
        self._verify_visible(
            p.get_by_text("Inbox (Request List) (All Requests)", exact=True),
            "Expected the Sent Requests inbox",
        )

    def find_sent_request(self, request_no: str) -> SentRequestRecord:
        """Spec §2-3: match by Request No. before reading status — never
        assume the first row is the intended one. Cell order follows the
        confirmed observed column order (S.No., Request No./PEN,
        Requested By, Requested To, Closed/Auto Closed By, Request
        Status, Action) — a spec-confirmed order, not a positional guess.
        """
        p = self.page
        row = p.get_by_role("row").filter(has_text=request_no)
        self._verify_visible(row, f"Expected a Sent Requests row for {request_no!r}")
        cells = row.get_by_role("cell")
        raw_status = (cells.nth(5).text_content() or "").strip()
        return SentRequestRecord(
            request_no=request_no,
            pen=(cells.nth(1).text_content() or "").strip(),
            requested_by=(cells.nth(2).text_content() or "").strip(),
            requested_to=(cells.nth(3).text_content() or "").strip(),
            closed_by=(cells.nth(4).text_content() or "").strip(),
            raw_status=raw_status,
            normalized_status=normalize_release_request_status(raw_status),
        )

    def open_sent_request_student_details(self, request_no: str) -> SentRequestStudentSnapshot:
        """Spec §5 — "Student Details (At the time the request was
        generated)": verify the request belongs to the intended student
        before acting on it."""
        p = self.page
        row = p.get_by_role("row").filter(has_text=request_no)
        row.get_by_role("button", name="Student Details").click()
        self._verify_visible(
            p.get_by_text(
                "Student Details (At the time the request was generated)", exact=True
            ),
            "Expected the Student Details snapshot modal",
        )
        return SentRequestStudentSnapshot(
            request_no=request_no,
            pen=p.get_by_label(ci_exact("PEN")).input_value(),
            student_name=p.get_by_label(ci_exact("Student Name")).input_value(),
            mother_name=p.get_by_label(ci_exact("Mother's Name")).input_value(),
            dob=p.get_by_label(ci_exact("DOB")).input_value(),
            father_name=p.get_by_label(ci_exact("Father's Name")).input_value(),
            class_name=p.get_by_label(ci_exact("Class")).input_value(),
        )

    # ===== ND Reconciliation (spec §165/§260-263) =====
    def search_for_nd_reconciliation(
        self, class_name: str, student_name: str
    ) -> list[NdReconciliationCandidate]:
        """spec §165.2/§260: select class first, then search by name.

        Assumption flagged (needs live-DOM verification, same posture as
        other flagged assumptions in this codebase e.g.
        field_mapping.py's Birth City stand-in): reuses the confirmed
        Global Student Search screen with a "Student Name" search mode,
        mirroring PEN Import's confirmed "Student PEN" mode — no
        recording separately confirms this screen's exact DOM for a
        name-based search. Returns every candidate row; the caller must
        apply the multi-attribute identity check (spec §165.3) — this
        method never silently picks one.
        """
        p = self.page
        p.get_by_text(ci_exact("Global Student Search")).click()
        p.get_by_label(ci_exact("Class")).select_option(label=class_name)
        p.get_by_label(ci_exact("Search By Name")).check()
        p.get_by_label(ci_exact("Name")).fill(student_name)
        p.get_by_role("button", name=ci_exact("Search")).click()
        self._verify_visible(
            p.get_by_text(ci_exact("Search Results")),
            "Expected ND reconciliation search results",
        )
        rows = p.get_by_role("row")
        candidates: list[NdReconciliationCandidate] = []
        for i in range(1, rows.count()):  # row 0 is the header row
            cells = rows.nth(i).get_by_role("cell")
            candidates.append(
                NdReconciliationCandidate(
                    student_name=(cells.nth(0).text_content() or "").strip(),
                    dob=(cells.nth(1).text_content() or "").strip(),
                    gender=(cells.nth(2).text_content() or "").strip(),
                    class_name=(cells.nth(3).text_content() or "").strip(),
                    current_pen=(cells.nth(4).text_content() or "").strip(),
                )
            )
        return candidates

    # -- shared verification helper ---------------------------------------
    def _verify_visible(self, locator: Locator, expected_description: str) -> None:
        try:
            expect(locator).to_be_visible(timeout=self.timeout_ms)
        except AssertionError:
            log_event(
                _logger, logging.ERROR, "expected state not observed",
                portal="NATIONAL_UDISE", expected_state=expected_description,
                url=self.page.url, page_title=self.page.title(),
            )
            raise ConsequentialActionUnverifiedError(expected_description) from None
