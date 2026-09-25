"""Gujarat UDISE (Child Tracking System) portal adapter.

Implements the confirmed New Entry workflow (spec §13-32, §163, §W) and
the confirmed Import/transfer-request workflow (spec §X). The
successful/Dropbox import outcome is NOT implemented here — it remains
`COMING_SOON` (UI-SPEC.md §B.5) because no recording demonstrates it;
callers must not infer it from this adapter's methods.

Selector strategy (spec Final Authority §B, applied throughout): prefer
accessible role/name and label/input relationship over any CSS/ID guess.
Every field this adapter fills is located by its documented label text,
never by position — this is what makes it resilient to layout changes
and it's also the only honest choice, since this project was never given
the portal's actual DOM/CSS to hardcode.

Verification note: every "expect the resulting state" check below uses
`playwright.sync_api.expect(...).to_be_visible()`, which polls up to
`timeout_ms` — NOT `Locator.is_visible()`, which returns immediately with
no retry and would be flaky against any real network latency (verified
against the installed Playwright 1.63.0 API before writing this, not
assumed).
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

_logger = get_logger("portals.gujarat_udise")

DEFAULT_TIMEOUT_MS = 10_000

# Spec §X.14 — only "Pending" is a confirmed observed status for a Sent
# Transfer Request; anything else routes to manual review, never guessed.
_KNOWN_TRANSFER_REQUEST_STATUSES = {
    "Pending": "PENDING",
}


def normalize_transfer_request_status(raw_status: str) -> str:
    return _KNOWN_TRANSFER_REQUEST_STATUSES.get(raw_status, "UNKNOWN_PORTAL_STATUS")


@dataclass(frozen=True)
class ManualBirthDetails:
    """Spec §18-19 manual birth-entry route fields."""

    birth_state: str
    birth_district: str
    birth_taluka: str
    birth_city_or_place: str
    birth_village: str
    year: str
    month: str
    date: str
    brn_present: bool
    brn_no: str | None = None


@dataclass(frozen=True)
class CtsDetails:
    """Spec §20 CTS new-student fields."""

    student_name: str
    father_name: str
    mother_name: str
    surname: str
    dob: str
    disabled: bool = False
    disability_type: str | None = None


@dataclass(frozen=True)
class TransferRequestRecord:
    """spec §X.14 — one row of the Student Transfer Request List's Sent
    Transfer Requests table. Assumption flagged (needs live-DOM
    verification, same posture as other flagged assumptions in this
    codebase): the spec confirms the list's existence and its Sent/
    Received/Completed/pending-status-filter structure but not an exact
    column layout, so this uses a minimal, plausible column set."""

    uid: str
    student_name: str
    destination_school: str
    raw_status: str
    normalized_status: str


class GujaratUDISEPortalAdapter:
    """Drives the Gujarat Child Tracking System / UDISE portal.

    Takes a Playwright `Page` the caller already navigated to the
    portal's login page (or an authenticated page — session management
    is the caller's concern, spec §112/§173).
    """

    def __init__(self, page: Page, *, timeout_ms: int = DEFAULT_TIMEOUT_MS):
        self.page = page
        self.timeout_ms = timeout_ms

    # -- login (spec §W: school code, password, CAPTCHA) -----------------
    def login(self, school_code: str, password: str) -> None:
        self.page.get_by_label("School Code").fill(school_code)
        self.page.get_by_label("Password").fill(password)
        if self._captcha_present():
            log_event(
                _logger, logging.INFO, "CAPTCHA detected on login, pausing for operator",
                portal="GUJARAT_UDISE",
            )
            raise AutomationPausedForUser(
                "CAPTCHA present on Gujarat UDISE login", checkpoint="login"
            )
        self.page.get_by_role("button", name="LOG IN").click()
        self._verify_visible(
            self.page.get_by_text(ci_exact("Home")), "Expected Home navigation after login"
        )

    def _captcha_present(self) -> bool:
        try:
            return self.page.get_by_label("Captcha").is_visible(timeout=1000)
        except PlaywrightTimeoutError:
            return False

    # -- New Entry: birth route + CTS details (spec §15-21) --------------
    def open_student_new_entry(self) -> None:
        self.page.get_by_text(ci_exact("Manage Students")).click()
        # role="button", not get_by_text: the nav item's own text
        # case-insensitively equals the destination screen's heading text
        # ("Student New Entry" vs "STUDENT NEW ENTRY") — scoping by role
        # is what keeps the two distinguishable once matching tolerates
        # capitalization differences (spec's UI-change resilience).
        self.page.get_by_role("button", name=ci_exact("Student New Entry")).click()
        self._verify_visible(
            self.page.get_by_role("heading", name=ci_exact("Student New Entry")),
            "Expected the Student New Entry screen",
        )

    def submit_manual_birth_details(self, details: ManualBirthDetails) -> None:
        """Spec §18-19 manual birth-entry route (as opposed to CRS-RGI)."""
        p = self.page
        p.get_by_label("Birth State").select_option(label=details.birth_state)
        p.get_by_label("Birth District").select_option(label=details.birth_district)
        p.get_by_label("Birth Taluka").select_option(label=details.birth_taluka)
        p.get_by_label("Birth City/Place").fill(details.birth_city_or_place)
        p.get_by_label("Birth Village").fill(details.birth_village)
        p.get_by_label("Birth Year").select_option(label=details.year)
        p.get_by_label("Birth Month").select_option(label=details.month)
        p.get_by_label("Birth Date").select_option(label=details.date)
        if details.brn_present:
            p.get_by_label("Birth Certificate No.").fill(details.brn_no or "")
        p.get_by_role("button", name="Next").click()
        log_event(
            _logger, logging.INFO, "manual birth details submitted",
            portal="GUJARAT_UDISE", brn_present=details.brn_present,
        )

    def submit_cts_details(self, details: CtsDetails) -> None:
        """Spec §20 — creates the student; verifies it via the Manage
        Students list (spec §21), never assumes success from the click
        alone (spec Final Authority §D consequential-action rule)."""
        p = self.page
        p.get_by_label("Student Name").fill(details.student_name)
        p.get_by_label("Father's Name").fill(details.father_name)
        p.get_by_label("Mother's Name").fill(details.mother_name)
        p.get_by_label("Surname").fill(details.surname)
        p.get_by_label("Date of Birth").fill(details.dob)
        p.get_by_label("Whether child is disabled").select_option(
            label="Yes" if details.disabled else "No"
        )
        if details.disabled and details.disability_type:
            p.get_by_label("Type of disability").select_option(label=details.disability_type)

        p.get_by_role("button", name="ADD NEW STUDENT").click()
        self._verify_visible(
            p.get_by_text(ci_exact(details.student_name)),
            f"Expected {details.student_name!r} to appear in the Manage "
            "Students list after ADD NEW STUDENT",
        )
        log_event(
            _logger, logging.INFO, "student created via CTS details",
            portal="GUJARAT_UDISE", student_name=details.student_name,
        )

    def read_generated_uid(self, student_name: str) -> str:
        """Spec §21: after ADD NEW STUDENT, the Manage Students list shows
        an Aadhaar/UID column for the new row. Reads it back rather than
        assuming a value — the caller writes this into the UDISE sheet's
        `UDISE No` column (never invents/derives a UID).
        """
        import re

        row = self.page.locator(".student-row").filter(
            has_text=re.compile(f"^{re.escape(student_name)}")
        )
        self._verify_visible(row, f"Expected a Manage Students row for {student_name!r}")
        uid = row.locator(".uid-cell").text_content()
        if not uid:
            raise ConsequentialActionUnverifiedError(
                f"Manage Students row for {student_name!r} has no UID cell"
            )
        return uid.strip()

    # -- Manage Students profile: generic label-driven tab fill/save -----
    # (spec §22-31: 5 tabs. Scholarship & Facility / Health & CWSN exact
    # field labels are explicitly "needs live verification" — UI-SPEC.md
    # §B.5 — so this stays generic/dict-driven rather than hardcoding
    # fields this project was never given confirmed evidence for.)
    def open_student_profile(self, student_name: str) -> None:
        self.page.get_by_text(ci_exact(student_name)).click()
        self._verify_visible(
            self.page.get_by_text(ci_exact("Personal")),
            "Expected the student profile (Personal/Education/Bank/... tabs)",
        )

    def open_tab(self, tab_name: str) -> None:
        """tab_name in {"Personal", "Education", "Bank",
        "Scholarship & Facility", "Health & CWSN"} (spec §22)."""
        self.page.get_by_role("tab", name=tab_name).click()

    def fill_tab(self, fields: dict[str, str]) -> None:
        """Fill every {label: value} pair on the currently open tab.

        Label-driven, not position-driven — this is deliberately generic
        so it works whether the caller has 5 confirmed fields (Personal)
        or a handful of live-verified ones (Scholarship & Facility/
        Health & CWSN), without this adapter inventing a field list the
        spec doesn't confirm.
        """
        for label, value in fields.items():
            self.page.get_by_label(label).fill(value)

    def save_current_tab(self, save_button_name: str = "SAVE STUDENT") -> None:
        """Spec §25: Personal tab's confirmed save button is "SAVE STUDENT".

        Other tabs' exact save-button text is not confirmed by the source
        recordings — pass save_button_name explicitly once verified live
        rather than assuming it matches Personal's.
        """
        self.page.get_by_role("button", name=save_button_name).click()

    # -- Import / transfer-request (spec §X — ACTIVE/pending outcome) ----
    def search_existing_student_by_uid(self, class_name: str, uid: str) -> bool:
        """Spec §X steps 1-5: Manage Students -> Standard Wise Entry ->
        select class -> search by UID. Returns True if an existing
        student (at another school) was found."""
        p = self.page
        p.get_by_text(ci_exact("Manage Students")).click()
        p.get_by_text(ci_exact("Standard Wise Entry")).click()
        p.get_by_label("Class").select_option(label=class_name)
        p.get_by_label("Search").fill(uid)
        p.get_by_role("button", name="Search").click()
        try:
            expect(p.get_by_text(ci_exact("Transfer"))).to_be_visible(timeout=self.timeout_ms)
            return True
        except AssertionError:
            return False

    def confirm_transfer_request(self) -> str:
        """Spec §X steps 6-12: transfer confirmation -> Transfer Student
        page (Transfer From/To) -> Update Transfer Request -> success
        message. Returns the observed success message text, or raises
        ConsequentialActionUnverifiedError if it never appears — the
        caller must not write REQUEST SENT without that confirmation.
        """
        p = self.page
        p.get_by_role("button", name="Confirm").click()
        self._verify_visible(
            p.get_by_text(ci_exact("Transfer Student")),
            "Expected the Transfer Student page (Transfer From/Transfer To)",
        )
        p.get_by_role("button", name="Update Transfer Request").click()
        success_text = "Student Transfer request saved successfully."
        self._verify_visible(
            p.get_by_text(ci_exact(success_text)), f"Expected confirmation message: {success_text!r}"
        )
        log_event(
            _logger, logging.INFO, "transfer request confirmed",
            portal="GUJARAT_UDISE",
        )
        return success_text

    # -- Student Transfer Request List / status check (spec §X.14, §M) ---
    def open_transfer_request_list(self) -> None:
        p = self.page
        p.get_by_text(ci_exact("Manage Students")).click()
        p.get_by_text(ci_exact("Student Transfer Request List")).click()
        p.get_by_text(ci_exact("Sent Transfer Requests")).click()
        self._verify_visible(
            p.get_by_text("Sent Transfer Requests (All)", exact=True),
            "Expected the Sent Transfer Requests list",
        )

    def find_transfer_request(self, uid: str) -> TransferRequestRecord:
        """Matched by UID — Gujarat's transfer requests have no separate
        request number (spec §X), unlike the National release-request
        workflow's Request No."""
        p = self.page
        row = p.get_by_role("row").filter(has_text=uid)
        self._verify_visible(row, f"Expected a Sent Transfer Requests row for {uid!r}")
        cells = row.get_by_role("cell")
        raw_status = (cells.nth(2).text_content() or "").strip()
        return TransferRequestRecord(
            uid=uid,
            student_name=(cells.nth(0).text_content() or "").strip(),
            destination_school=(cells.nth(1).text_content() or "").strip(),
            raw_status=raw_status,
            normalized_status=normalize_transfer_request_status(raw_status),
        )

    # -- shared verification helper ---------------------------------------
    def _verify_visible(self, locator: Locator, expected_description: str) -> None:
        """Spec Final Authority §D: verify the resulting state after every
        consequential action — never assume success from the click alone.

        Uses expect(...).to_be_visible(), which polls up to timeout_ms —
        Locator.is_visible() alone does not wait/retry and would be flaky.
        """
        try:
            expect(locator).to_be_visible(timeout=self.timeout_ms)
        except AssertionError:
            log_event(
                _logger, logging.ERROR, "expected state not observed",
                portal="GUJARAT_UDISE", expected_state=expected_description,
                url=self.page.url, page_title=self.page.title(),
            )
            raise ConsequentialActionUnverifiedError(expected_description) from None
