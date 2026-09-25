"""Automation Coverage (UI-SPEC.md §B.5): an explicit, always-visible map
of which workflow branches are fully automated vs. still manual, and
*why* — this is the UI's answer to spec §AH: never silently guess or
silently skip an unresolved workflow, show the boundary instead.

Content mirrors UI-SPEC.md §B.5's table exactly (2026-09-25) — this is
reference/documentation content, not derived from live data, so it's
kept here as the single source the screen renders, matching that table
verbatim. Keep both in sync if either changes.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.app.app_context import AppContext
from src.app.widgets import screen_header

# (workflow, status, why) — verbatim from UI-SPEC.md §B.5.
_COVERAGE_ROWS: list[tuple[str, str, str]] = [
    ("UDISE New Entry (all 5 profile tabs)", "Automated",
     "Full click sequence confirmed, spec §163/§W"),
    ("  ↳ Scholarship & Facility / Health & CWSN exact fields", "Needs live-DOM verification",
     "Spec §30/§31/§W: \"not completely machine-readable in every frame\""),
    ("PEN New Entry (4 profile stages)", "Automated",
     "Full click sequence confirmed, spec §164/§Y"),
    ("  ↳ Aadhaar consent", "Always manual (policy)",
     "Spec §39/§142/§I — legal confirmation, not an evidence gap"),
    ("UDISE Import — pending/request-sent outcome", "Automated",
     "Exact click sequence confirmed, spec §X"),
    ("UDISE Import — successful/Dropbox outcome", "Manual for now",
     "Outcome rule confirmed (spec §295) but spec §295.3 says exact portal "
     "screen/button names must come from a dedicated recording — not yet given"),
    ("PEN Import — Other School ACTIVE (pending) outcome", "Automated",
     "Full click-by-click workflow confirmed from the recording — Aadhaar-"
     "duplicate check, Track By Details, Global Student Search, Student "
     "Status, HOS Details, IMPORT PENDING sheet write"),
    ("PEN Import — successful/Dropbox outcome", "Manual for now",
     "Still not demonstrated by any recording; do not infer it from the "
     "ACTIVE-outcome workflow"),
    ("Condition 4 — both imports resolve to their pending outcome", "Automated",
     "Composable from two confirmed pieces: UDISE Import ACTIVE + PEN Import ACTIVE"),
    ("Condition 4 — either import resolves to its successful/Dropbox outcome", "Manual for now",
     "Composition includes an unconfirmed piece — no recording demonstrates "
     "the successful path for either portal"),
    ("ND reconciliation", "Automated", "Full sequence confirmed, spec §V/§165"),
    ("Gujarat transfer-request status monitoring", "Automated",
     "Full rule confirmed, spec §M-§O, §X"),
    ("PEN Request Sent (Student Release Request generation)", "Automated",
     "Full click sequence confirmed, master spec \"PEN REQUEST SENT\" section"),
    ("View Sent Request / National release-request monitoring", "Automated",
     "Confirmed exact status wording (\"Pending at Destination\") and "
     "request-list fields"),
    ("CAPTCHA / OTP", "Always manual (policy)",
     "Spec §I — security boundary, not an evidence gap"),
]

_STATUS_CHIP_KIND = {
    "Automated": "green",
    "Needs live-DOM verification": "amber",
    "Manual for now": "plum",
    "Always manual (policy)": "navy",
}


class AutomationCoverageScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "Automation Coverage",
                "What's really automated vs. still manual, and why — never "
                "silently guessed or silently skipped (spec §AH). Only the "
                "successful/Dropbox outcome for UDISE or PEN Import remains "
                "genuinely unconfirmed as of 2026-09-25.",
            )
        )

        table = QTableWidget(len(_COVERAGE_ROWS), 3)
        table.setHorizontalHeaderLabels(["Workflow", "Status", "Why"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setWordWrap(True)
        table.horizontalHeader().resizeSection(1, 190)
        for row, (workflow, status, why) in enumerate(_COVERAGE_ROWS):
            table.setItem(row, 0, QTableWidgetItem(workflow))
            chip = QLabel(status)
            chip.setProperty("chip", _STATUS_CHIP_KIND.get(status, "muted"))
            table.setCellWidget(row, 1, chip)
            table.setItem(row, 2, QTableWidgetItem(why))
        table.resizeRowsToContents()
        layout.addWidget(table, stretch=1)
