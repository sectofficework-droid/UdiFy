"""Shared portal-adapter types.

Portal-specific navigation, selectors, statuses, dialogs, and workflows
stay in their own adapter classes (spec decision §3) — this module only
holds what's genuinely common: the two portal identities, and the
verification-failure exceptions every adapter raises the same way.
"""

from __future__ import annotations

from enum import Enum


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
