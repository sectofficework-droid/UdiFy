"""Unrecognized portal status handling (TODO.md mock scenario checklist:
"Portal status unknown", both portals) — never silently mapped, always
routed to manual review via the UNKNOWN_PORTAL_STATUS classification
(DB-DESIGN.md §C.3c/§C.3d)."""

from __future__ import annotations

from src.db.approval_checks import classify_status_check
from src.portals.udise_gujarat.adapter import normalize_transfer_request_status
from src.portals.udise_plus.adapter import normalize_release_request_status


def test_national_unrecognized_status_is_never_guessed():
    assert normalize_release_request_status("Pending at Destination") == "PENDING_AT_DESTINATION"
    assert normalize_release_request_status("Some New Portal Wording") == "UNKNOWN_PORTAL_STATUS"
    assert normalize_release_request_status("") == "UNKNOWN_PORTAL_STATUS"


def test_gujarat_unrecognized_status_is_never_guessed():
    assert normalize_transfer_request_status("Pending") == "PENDING"
    assert normalize_transfer_request_status("Some New Portal Wording") == "UNKNOWN_PORTAL_STATUS"


def test_unknown_status_always_classifies_as_unknown_regardless_of_previous():
    """spec §3: an unrecognized status always routes to manual review,
    even if it happens to equal the previous check's normalized value —
    unlike STILL_PENDING/STATUS_CHANGED, "unknown" is never conditional
    on history."""
    assert classify_status_check("UNKNOWN_PORTAL_STATUS", None) == "UNKNOWN_PORTAL_STATUS"
    assert (
        classify_status_check("UNKNOWN_PORTAL_STATUS", "UNKNOWN_PORTAL_STATUS")
        == "UNKNOWN_PORTAL_STATUS"
    )


def test_still_pending_vs_status_changed_classification():
    assert classify_status_check("PENDING_AT_DESTINATION", "PENDING_AT_DESTINATION") == "STILL_PENDING"
    assert classify_status_check("PENDING_AT_DESTINATION", None) == "STILL_PENDING"
    assert classify_status_check("APPROVED", "PENDING_AT_DESTINATION") == "STATUS_CHANGED"
