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
)

_logger = get_logger("portals.national_udise")

DEFAULT_TIMEOUT_MS = 10_000

AADHAAR_ALREADY_REGISTERED_TEXT = "AADHAAR number is already registered with some other student"
INITIALIZATION_SUCCESS_TEXT = "The Student has been initialised/Saved Successfully."
PROFILE_COMPLETE_TEXT = "Data completion is complete."


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
            p.get_by_text(INITIALIZATION_SUCCESS_TEXT, exact=True),
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
            p.get_by_text(PROFILE_COMPLETE_TEXT, exact=True),
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
        p.get_by_label("Check AADHAAR Number Availability").check()
        p.get_by_label("Aadhaar Number").fill(aadhaar)
        p.get_by_role("button", name="Go").click()
        try:
            expect(
                p.get_by_text(AADHAAR_ALREADY_REGISTERED_TEXT, exact=True)
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
            p.get_by_text("Track By Details", exact=True),
            "Expected the Track By Details screen",
        )
        return TrackByDetailsResult(
            student_pen=p.get_by_label("Student PEN").input_value(),
            student_name=p.get_by_label("Student Name").input_value(),
            source_school_udise=p.get_by_label("UDISE Code").input_value(),
            source_school_name=p.get_by_label("School Name").input_value(),
        )

    def global_student_search_by_pen(self, pen: str) -> GlobalSearchResult:
        """Spec steps 11-13: Global Student Search, mode = Student PEN.
        `student_status` is the decisive field (spec §13) — the caller
        must check it explicitly, this adapter never interprets it."""
        p = self.page
        p.get_by_text("Global Student Search", exact=True).click()
        p.get_by_label("Student PEN").check()
        p.get_by_label("PEN").fill(pen)
        p.get_by_role("button", name="Search").click()
        self._verify_visible(
            p.get_by_label("Student Status"), "Expected a Global Student Search result"
        )
        return GlobalSearchResult(
            student_name=p.get_by_label("Student Name").input_value(),
            pen=pen,
            student_status=p.get_by_label("Student Status").input_value(),
            source_school_name=p.get_by_label("School Details").input_value(),
            source_school_udise=p.get_by_label("School UDISE").input_value(),
        )

    def open_hos_details(self) -> HosDetails:
        """Spec step 14 — source school's HOS info. Handle with care: this
        is another school's staff contact info, not this school's (see
        SECURITY-THREAT-MODEL.md's dedicated threat row)."""
        p = self.page
        p.get_by_role("button", name="HOS Details").click()
        self._verify_visible(
            p.get_by_text("HOS Details", exact=True), "Expected the HOS Details modal"
        )
        return HosDetails(
            state=p.get_by_label("State").input_value(),
            district=p.get_by_label("District").input_value(),
            block=p.get_by_label("Block").input_value(),
            hos_name=p.get_by_label("Headmaster/Principal").input_value(),
            hos_contact=p.get_by_label("Contact No.").input_value(),
        )

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
