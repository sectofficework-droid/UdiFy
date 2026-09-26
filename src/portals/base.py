"""Shared portal-adapter types.

Portal-specific navigation, selectors, statuses, dialogs, and workflows
stay in their own adapter classes (spec decision §3) — this module only
holds what's genuinely common: the two portal identities, and the
verification-failure exceptions every adapter raises the same way.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from playwright.sync_api import Page, expect


def ci_exact(text: str) -> re.Pattern[str]:
    """A whole-string, case-insensitive match for get_by_text/get_by_label/
    get_by_role(name=...).

    Spec's "UI CHANGE HANDLING" acceptance tests require tolerating "minor
    text punctuation/capitalization changes" while still treating a
    genuinely different state as unrecognized. Plain `exact=True` is
    case-SENSITIVE — it was adopted elsewhere in these adapters only to
    stop a short confirmed label from ambiguously substring-matching a
    longer one on the same screen (e.g. "PEN" vs "Student PEN"), not to
    demand exact casing. This keeps that whole-string precision while
    adding the capitalization tolerance the spec explicitly requires.
    """
    return re.compile(r"^\s*" + re.escape(text.strip()) + r"\s*$", re.IGNORECASE)


def labeled_input(page: Page, label_substring: str):
    """`get_by_label`, scoped to `<input>` elements only.

    Found live 2026-09-26 against both real portals (not reachable from
    the mock fixtures, which never modeled this): a password field's
    accessible name ambiguously substring-matches a separate "Show/Toggle
    password" visibility button on the same page — a modern UI pattern
    neither original mock fixture included. Plain `get_by_label` there
    hits Playwright's strict-mode violation (2 elements), and switching
    to `ci_exact` instead breaks the match entirely, since the real
    field's accessible name carries extra decoration (an icon glyph, a
    required-field "*") that isn't just the label text — the real label
    was never as clean as the mock's. This keeps substring/case-
    insensitive tolerance (still needed for that decoration) while the
    `<input>` filter excludes the sibling `<button>` the plain substring
    match can't otherwise tell apart from the real field.
    """
    return page.get_by_label(label_substring).and_(page.locator("input"))


class PortalName(str, Enum):
    GUJARAT_UDISE = "GUJARAT_UDISE"
    NATIONAL_UDISE = "NATIONAL_UDISE"


class PortalError(Exception):
    """Base class for portal-adapter errors."""


class UnknownPortalStateError(PortalError):
    """The page is not one of the states this adapter recognizes.

    Per spec Final Authority §C4 / decision §9: never guess here. The
    caller must capture diagnostics and stop for manual intervention —
    this exception exists so "unknown state" is a distinct, structured
    signal, not just any exception.
    """


class ConsequentialActionUnverifiedError(PortalError):
    """An action was performed but its expected resulting state could
    not be confirmed. Never treated as success (spec Final Authority §J:
    never mark GREEN/complete solely because a button was clicked)."""


class AutomationPausedForUser(PortalError):
    """CAPTCHA, OTP, or another mandatory security interaction was
    encountered (spec decision §7). Not a failure — a deliberate,
    expected pause. The caller resumes from the checkpoint once the
    operator has completed the manual step."""

    def __init__(self, reason: str, checkpoint: str):
        super().__init__(reason)
        self.checkpoint = checkpoint


# ===================== Generic, portal-agnostic helpers =====================
# Neither of these is wired into any condition branch or adapter method.
# No source recording demonstrates a file-upload screen or a dependent/
# cascading-dropdown delay on either portal (TODO.md testing-matrix gaps:
# "Safe file uploads", "Correct dependent-dropdown handling") — inventing
# selectors for a screen nobody has seen would violate the same rule that
# keeps every other selector in these adapters role/label/exact-text-based
# from an actual recording (Final Authority §B; RULEBOOK §J14: no invented
# scope). These exist so a real adapter method can be built quickly, once
# a recording confirms one, without re-deriving the Playwright mechanics —
# they take a `Page` and confirmed label text, same as every other
# selector in this project, and do nothing else.

def set_file_input(page: Page, label: str, file_path: str | Path) -> None:
    """Sets a `<input type="file">` identified by its confirmed label.
    Never invents a selector — the caller supplies the exact label text
    from a real, recorded portal screen."""
    page.get_by_label(label).set_input_files(str(file_path))


def wait_for_dependent_option(
    page: Page, dropdown_label: str, option_label: str, *, timeout_ms: int = 5000,
) -> None:
    """Waits for a dependent/cascading `<select>` (identified by
    `dropdown_label`) to have populated an `option_label` option — e.g.
    after a parent dropdown's selection triggers an async fetch — before
    selecting it. Playwright's default actionability waits already cover
    every dependent-dropdown case in the fixtures tested so far; this
    exists for the case where a future confirmed screen needs an explicit
    wait beyond that default.
    """
    dropdown = page.get_by_label(dropdown_label)
    option = dropdown.locator("option").filter(has_text=option_label)
    expect(option).to_be_attached(timeout=timeout_ms)
    dropdown.select_option(label=option_label)
