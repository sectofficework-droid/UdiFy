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
import re
from dataclasses import dataclass

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.diagnostics.logging_setup import get_logger, log_event
from src.portals.base import (
    AutomationPausedForUser,
    ConsequentialActionUnverifiedError,
    ci_exact,
    password_input,
)

_logger = get_logger("portals.national_udise")

DEFAULT_TIMEOUT_MS = 10_000

AADHAAR_ALREADY_REGISTERED_TEXT = "AADHAAR number is already registered with some other student"
PROFILE_COMPLETE_TEXT = "Data completion is complete."
IDENTITY_CONFIRMATION_HEADING = "Confirm the following details are correct"
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
    """Class/section context for open_add_student() (spec §37). Real
    navigation confirmed 2026-09-27 goes through the School Dashboard's
    class row, not a dropdown — student_name is filled later via
    StudentIdentityFields/fill_identity_fields(), not at navigation time,
    but is kept here since callers already have all three values
    together (e.g. field_mapping.py's pen_row_to_new_student_init)."""

    student_name: str
    class_name: str
    section: str


@dataclass(frozen=True)
class StudentIdentityFields:
    """The identity fields the real portal locks permanently once
    confirmed (see read_identity_confirmation()'s docstring) — kept as
    their own dataclass rather than folded into fill_general_profile()'s
    generic dict, so a caller can never accidentally skip verifying them
    before confirm_identity_details() (Final Authority)."""

    student_name: str
    gender: str
    dob: str
    mother_name: str
    father_name: str


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
        # password_input, not get_by_label: see its docstring — the real
        # portal's password field/visibility-toggle button ambiguity
        # (found 2026-09-26 against the live portal) needed the field's
        # actual type="password" attribute, not label-text matching.
        password_input(self.page).fill(password)
        if self._captcha_present():
            log_event(
                _logger, logging.INFO, "CAPTCHA detected on login, pausing for operator",
                portal="NATIONAL_UDISE",
            )
            raise AutomationPausedForUser(
                "CAPTCHA present on National UDISE+ login", checkpoint="login"
            )
        # The real button reads "Sign In"; the mock fixture (built before
        # this was ever checked against the actual portal) uses "Login".
        # Accept either rather than picking one and breaking the other.
        self.page.get_by_role(
            "button", name=re.compile(r"^\s*(Login|Sign In)\s*$", re.IGNORECASE)
        ).click()
        self._verify_login_succeeded()

    def _verify_login_succeeded(self) -> None:
        # Real bug found live 2026-09-27: until this check existed,
        # login() had NO post-click verification at all - it just
        # clicked Sign In and returned. A rejected captcha (real portal
        # shows an "Invalid Captcha" toast and stays on the login page)
        # therefore silently reported as a successful login, since no
        # exception was ever raised either way.
        #
        # Confirmed live: a successful login lands on
        # https://sdms.udiseplus.gov.in/one-view/dashboard, headed
        # "Welcome <name>," - checked via that text (not the URL), since
        # the mock fixture's login is a same-URL template swap and never
        # navigates anywhere (tests/fixtures/udise_plus/new_pen_entry.html
        # updated with a matching "Welcome" marker on its own post-login
        # screen so this one check covers both real and mock).
        try:
            expect(self.page.get_by_text(re.compile(r"Welcome", re.IGNORECASE))).to_be_visible(
                timeout=self.timeout_ms
            )
        except AssertionError:
            log_event(
                _logger, logging.ERROR, "expected state not observed",
                portal="NATIONAL_UDISE",
                expected_state="post-login 'Welcome' text",
                url=self.page.url, page_title=self.page.title(),
            )
            raise ConsequentialActionUnverifiedError(
                "Expected navigation to the UDISE+ Common Module after Sign "
                "In - login not confirmed (wrong captcha/credentials, or an "
                "unrecognized page/state)"
            ) from None

    def _captcha_present(self) -> bool:
        # get_by_label("Captcha") doesn't reach the real field: dumped
        # every <input>/<label> on the live page 2026-09-26 and the
        # "Captcha" <label> has no `for` attribute and isn't wrapped
        # around anything — it's not associated with the answer field by
        # any mechanism get_by_label relies on. The actual field is
        # `<input type="text" name="captcha" placeholder="Enter captcha
        # code">`, confirmed directly from that dump, not guessed — same
        # confidence level as using type="password" elsewhere.
        #
        # Checks the field's *value*, not just its visibility: the field
        # stays visible whether or not the operator has typed the code
        # into it, so a visibility-only check never clears once it first
        # fires — confirmed live 2026-09-26 (the operator solved the
        # captcha, but this kept reporting "still present" on retry). An
        # empty value means still waiting on the operator; once they've
        # typed something, that's the human confirmation this adapter
        # needs (it can't itself verify a captcha code is *correct* —
        # only the real portal can, on submission — so "operator entered
        # something" is the right/only signal available to act on here).
        try:
            field = self.page.locator('input[name="captcha"]')
            if not field.is_visible(timeout=1000):
                return False
            return field.input_value() == ""
        except PlaywrightTimeoutError:
            return False

    # ================= New PEN Entry (spec §37-53, §164, §Y) =================
    def open_students_module(self) -> None:
        """Real navigation confirmed 2026-09-27 (live + video review):
        after login, the portal lands on a hub page ("UDISE+ Common
        Module") with 4 module cards (School Directory, School Profile &
        Facilities, Teacher Module, Students Module) — NOT the School
        Dashboard directly. Students Module's "Go" button opens a NEW
        browser tab, landing on the academic-year-choice screen.

        This adapter re-points itself at that new tab (`self.page`) from
        here on, so every subsequent method (choose_current_academic_year,
        open_add_student, ...) keeps working transparently against it —
        the original hub-page tab is left open, untouched, in the
        background.
        """
        context = self.page.context
        with context.expect_page() as new_page_info:
            self.page.get_by_text("Students Module").locator(
                "xpath=ancestor::*[self::div or self::section][1]"
            ).get_by_role("button", name="Go").click()
        self.page = new_page_info.value
        self.page.wait_for_load_state("networkidle")
        log_event(_logger, logging.INFO, "opened Students Module", portal="NATIONAL_UDISE")

    def choose_current_academic_year(self) -> None:
        """Clicks the "Current Academic Year" card on the academic-
        choice screen, landing on the School Dashboard. `.first`:
        confirmed live — the phrase also appears a second time in a
        paragraph below the card ("navigate to the 'Current Academic
        year 2026-27' tab..."), so the bare locator matches 2 elements
        under Playwright's strict mode.
        """
        p = self.page
        option = p.get_by_text(re.compile(r"Current Academic Year", re.IGNORECASE)).first
        self._verify_visible(option, "Expected the 'Current Academic Year' card")
        option.click()
        p.wait_for_load_state("networkidle")
        self._verify_visible(
            p.get_by_text(re.compile(r"School Details\s*-\s*Grade Wise", re.IGNORECASE)),
            "Expected the School Dashboard after choosing academic year",
        )
        log_event(_logger, logging.INFO, "chose current academic year", portal="NATIONAL_UDISE")

    def dismiss_pending_notifications(self) -> None:
        """One or more "Notification" modals (pending release requests
        etc.) can appear stacked on the School Dashboard on arrival —
        confirmed live 2026-09-27, at least 2 in a row. Closing only one
        is not enough; keeps closing until none remain, capped so a
        genuinely stuck modal can't loop forever."""
        p = self.page
        # .first, not the bare locator: 2+ "Close" buttons can be visible
        # SIMULTANEOUSLY (stacked modals), and Playwright's is_visible/
        # click on a multi-match locator raise a strict-mode violation
        # rather than just reporting a count — hit this live.
        close_btn = p.get_by_role("button", name=re.compile(r"^Close$")).first
        for _ in range(5):
            try:
                if not close_btn.is_visible(timeout=2000):
                    break
            except PlaywrightTimeoutError:
                break
            close_btn.click()
            p.wait_for_timeout(300)
        log_event(_logger, logging.INFO, "dismissed pending notifications", portal="NATIONAL_UDISE")

    def open_add_student(self, details: NewStudentInit) -> None:
        """Real navigation confirmed 2026-09-27 by reviewing the source
        screen recording (UDISE/4 PEN ENTRY.mp4, the exact source
        UDIFY-SPECIFICATIONS.md §34 cites) — the previously-coded
        assumption here (a generic page with Class/Section dropdowns and
        an "Add New Student" button, reached directly after login, with
        its own "initialised/Saved Successfully" dialog) does not match
        the real portal at all; no such page or dialog appears anywhere
        in the recording.

        The real path: after login, the School Dashboard ("School
        Details - Grade Wise" table) lists one collapsed row per class.
        Clicking a class's row expands it, revealing "Add Student"/"View/
        Manage" action buttons — the original video-based read of this
        WAS correct; a later live diagnostic wrongly concluded otherwise
        because it read hidden DOM text (`textContent`, which ignores
        visibility) rather than what get_by_role's visibility-aware
        matching actually sees — confirmed live 2026-09-27 by the user
        directly, after a failed attempt with the click-less version.
        Clicking "Add Student" lands directly on the General Profile tab
        (tab 1 of 4) with Class/Section/Academic Year already fixed from
        context (shown as a locked breadcrumb) — not selectable here.

        Matching by class name alone is ambiguous when several classes
        share the same section value (confirmed live: every row's
        Section is "A" in this school) — `.filter(has_text=section)`
        narrows to the one row that has both (matching by hidden text is
        fine for identifying the right row; only clicking a hidden
        element is the problem, and the expand click below targets the
        always-visible row itself, not hidden content).

        The "Add Student" button is looked up page-wide after expanding,
        not scoped to the row locator — real DOM nesting (sibling row vs.
        descendant) isn't confirmed, and only one row is ever expanded at
        a time, so this avoids assuming a nesting structure and getting
        it wrong a third time.
        """
        p = self.page
        # Plain-string name matching (substring, case-insensitive) rather
        # than a regex: Playwright's role-selector engine mis-parses a
        # regex whose source contains "/" (e.g. "LKG/KG1/PP2") since it
        # uses /pattern/ as its own delimiter syntax — hit this live.
        class_rows = p.get_by_role("row", name=details.class_name)
        target_row = class_rows.filter(has_text=details.section) if details.section else class_rows
        # Click the class-NAME CELL specifically, not the row's overall
        # center — confirmed by re-examining the source recording frame
        # by frame: the cursor sits precisely over the class-name text
        # (leftmost column) at the moment of the successful click, not
        # over the row's full-width center (which for a wide table lands
        # on a completely different column with no click handler — this
        # was the actual reason 3 straight live attempts silently did
        # nothing after clicking the row as a whole).
        target_row.first.get_by_text(details.class_name).first.click()
        p.get_by_role("button", name=ci_exact("Add Student")).click()
        self._verify_visible(
            p.get_by_text(ci_exact("General Profile")),
            "Expected the General Profile tab after Add Student",
        )
        log_event(
            _logger, logging.INFO, "opened Add Student for class/section",
            portal="NATIONAL_UDISE", class_name=details.class_name, section=details.section,
        )

    def fill_identity_fields(self, fields: StudentIdentityFields) -> None:
        """Fills the identity fields at the top of General Profile, then
        clicks Save — which raises the real portal's own "Confirm the
        following details are correct" modal (confirmed live 2026-09-27,
        video review). Field labels are inferred from screen-recording
        pixels, not a live DOM dump — flagged, same posture as
        open_add_student() above.
        """
        p = self.page
        p.get_by_label(ci_exact("Student's Name")).fill(fields.student_name)
        p.get_by_label(ci_exact("Gender")).select_option(label=fields.gender)
        p.get_by_label(ci_exact("Date of Birth")).fill(fields.dob)
        p.get_by_label(ci_exact("Mother's Name")).fill(fields.mother_name)
        p.get_by_label(ci_exact("Father's Name")).fill(fields.father_name)
        p.get_by_role("button", name=ci_exact("Save")).click()

    def read_identity_confirmation(self) -> str:
        """Returns the identity-confirmation modal's full text, for the
        caller to verify against the source-of-truth spreadsheet row
        BEFORE calling confirm_identity_details() — the real portal's own
        warning is explicit: "The above information can not be changed
        once it has been confirmed." (confirmed live 2026-09-27).

        Returns raw text rather than a structured per-field dataclass:
        the modal's exact DOM (row structure per field) is confirmed only
        from screen-recording pixels, not a live dump — parsing it into
        named fields without that confirmation would be guessing a
        selector as fact (RULEBOOK.md K1). This adapter deliberately
        never does the identity comparison itself (same posture as
        TrackByDetailsResult/GlobalSearchResult elsewhere in this file) —
        that is the engine's Final Authority responsibility.
        """
        p = self.page
        modal = p.get_by_text(ci_exact(IDENTITY_CONFIRMATION_HEADING)).locator(
            "xpath=ancestor::*[self::div or self::section][1]"
        )
        self._verify_visible(modal, "Expected the identity-confirmation modal")
        return modal.text_content() or ""

    def confirm_identity_details(self) -> None:
        """Checks every checkbox in the identity-confirmation modal and
        clicks Confirm. The caller MUST have already verified
        read_identity_confirmation()'s text against the source-of-truth
        spreadsheet row (Final Authority) — this is a one-way action on
        the real portal (see read_identity_confirmation()'s docstring).
        """
        p = self.page
        modal = p.get_by_text(ci_exact(IDENTITY_CONFIRMATION_HEADING)).locator(
            "xpath=ancestor::*[self::div or self::section][1]"
        )
        for checkbox in modal.get_by_role("checkbox").all():
            checkbox.check()
        modal.get_by_role("button", name=ci_exact("Confirm")).click()
        log_event(_logger, logging.INFO, "identity details confirmed", portal="NATIONAL_UDISE")

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
