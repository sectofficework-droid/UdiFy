"""Approval / status-check batch flow (UI-SPEC.md §B.1, spec §M): a
single up-front confirmation for all LIGHT ORANGE / REQUEST SENT
students, then a combined report split into Still Pending and Status
Changed (the Status-Changed manual review queue)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from playwright.sync_api import sync_playwright

from src.app.app_context import AppContext
from src.app.widgets import status_chip, screen_header
from src.db.connection import connect
from src.engine.approval_batch import run_batch_status_check
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter

_FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
GUJARAT_FIXTURE = _FIXTURES_ROOT / "gujarat_udise" / "new_entry.html"
NATIONAL_FIXTURE = _FIXTURES_ROOT / "udise_plus" / "new_pen_entry.html"

_OPEN_CASE_QUERY = """
    SELECT request_case_id, student_id, case_type, portal, request_type,
           request_no, normalized_status
    FROM request_cases
    WHERE request_type != 'NONE' AND request_no IS NOT NULL
    ORDER BY created_at DESC
"""


class _BatchCheckWorker(QThread):
    finished_ok = Signal(dict)  # request_case_id -> ApprovalCheck
    failed = Signal(str)

    def __init__(self, sqlite_path, request_case_ids: list[str]):
        super().__init__()
        self.sqlite_path = sqlite_path
        self.request_case_ids = request_case_ids

    def run(self) -> None:  # noqa: overrides QThread.run
        conn = connect(self.sqlite_path)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                try:
                    gujarat_page = browser.new_page()
                    gujarat_page.goto(f"file:///{GUJARAT_FIXTURE.as_posix()}")
                    gujarat = GujaratUDISEPortalAdapter(gujarat_page, timeout_ms=5000)
                    gujarat.login("24224100067", "mock-password")

                    national_page = browser.new_page()
                    national_page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
                    national = NationalUDISEPortalAdapter(national_page, timeout_ms=5000)
                    national.login("sunil.pradhan", "mock-password")

                    results = run_batch_status_check(
                        gujarat, national, conn, self.request_case_ids, environment="MOCK",
                    )
                    self.finished_ok.emit(results)
                finally:
                    browser.close()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            conn.close()


class ApprovalMonitoringScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.worker: _BatchCheckWorker | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "Approval Monitoring",
                "Every LIGHT ORANGE / REQUEST SENT case across both portals, "
                "checked with ONE confirmation — never a per-student click "
                "(spec §M). A status change is never auto-acted on; it goes to "
                "manual review.",
            )
        )

        controls = QHBoxLayout()
        self.check_btn = QPushButton("Check all pending (both portals)")
        self.check_btn.clicked.connect(self._run_batch_check)
        controls.addWidget(self.check_btn)
        self.status_label = QLabel("")
        controls.addWidget(self.status_label)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Student", "Portal", "Case type", "Request/UID", "Status", "Classification"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        for col, width in ((1, 140), (2, 160), (3, 150), (4, 130), (5, 130)):
            self.table.horizontalHeader().resizeSection(col, width)
        layout.addWidget(self.table, stretch=1)

        self._populate()

    def on_shown(self) -> None:
        self._populate()

    def _open_cases(self) -> list:
        return list(self.ctx.conn.execute(_OPEN_CASE_QUERY))

    def _populate(self, classifications: dict[str, str] | None = None) -> None:
        rows = self._open_cases()
        self.table.setRowCount(len(rows))
        classifications = classifications or {}
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["student_id"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["portal"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["case_type"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["request_no"] or ""))
            status = row["normalized_status"] or "NOT YET CHECKED"
            self.table.setCellWidget(i, 4, status_chip(status))
            classification = classifications.get(row["request_case_id"], "")
            if classification:
                self.table.setCellWidget(i, 5, status_chip(classification))
            else:
                self.table.setItem(i, 5, QTableWidgetItem(""))

    def _run_batch_check(self) -> None:
        if self.worker is not None:
            return
        rows = self._open_cases()
        ids = [row["request_case_id"] for row in rows]
        if not ids:
            self.status_label.setText("No open request cases to check.")
            return
        self.check_btn.setEnabled(False)
        self.status_label.setText(f"Checking {len(ids)} case(s)…")
        self.worker = _BatchCheckWorker(self.ctx.settings.sqlite_path, ids)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_thread_finished)
        self.worker.start()

    def _on_finished(self, results: dict) -> None:
        still_pending = sum(1 for c in results.values() if c.classification == "STILL_PENDING")
        changed = sum(1 for c in results.values() if c.classification != "STILL_PENDING")
        self.status_label.setText(
            f"Checked {len(results)}: {still_pending} still pending, "
            f"{changed} need manual review."
        )
        classifications = {rid: c.classification for rid, c in results.items()}
        self._populate(classifications)

    def _on_failed(self, message: str) -> None:
        self.status_label.setText(f"Check failed: {message}")

    def _on_thread_finished(self) -> None:
        self.worker = None
        self.check_btn.setEnabled(True)
