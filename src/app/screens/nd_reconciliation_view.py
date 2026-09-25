"""ND Reconciliation view (UI-SPEC.md §B.1, spec §V): explicit, separately
triggered operation (never automatic) listing PEN=ND candidates and
reconciliation results."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from playwright.sync_api import sync_playwright

from src.app.app_context import AppContext
from src.app.mock_fixtures import NATIONAL_FIXTURE
from src.app.widgets import screen_header
from src.db.connection import connect
from src.engine.nd_reconciliation import run_nd_reconciliation
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter


class _NdReconciliationWorker(QThread):
    finished_ok = Signal(str)  # outcome string
    failed = Signal(str)

    def __init__(self, sqlite_path, sheets, student, class_name: str):
        super().__init__()
        self.sqlite_path = sqlite_path
        self.sheets = sheets
        self.student = student
        self.class_name = class_name

    def run(self) -> None:  # noqa: overrides QThread.run
        conn = connect(self.sqlite_path)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                try:
                    page = browser.new_page()
                    page.goto(f"file:///{NATIONAL_FIXTURE.as_posix()}")
                    national = NationalUDISEPortalAdapter(page, timeout_ms=5000)
                    national.login("sunil.pradhan", "mock-password")
                    outcome = run_nd_reconciliation(
                        national, self.sheets, conn, self.student,
                        class_name=self.class_name, environment="MOCK",
                    )
                    self.finished_ok.emit(outcome)
                finally:
                    browser.close()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            conn.close()


class NdReconciliationScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.worker: _NdReconciliationWorker | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "ND Reconciliation",
                "Explicit, separately-triggered check for whether a student "
                "whose PEN is still ND has since received an actual 11-digit "
                "PEN (spec §165/§259-264) — never run automatically as part "
                "of New PEN Entry.",
            )
        )

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Student", "Class", "Current PEN", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.horizontalHeader().resizeSection(3, 110)
        layout.addWidget(self.table, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self._populate()

    def on_shown(self) -> None:
        self._populate()

    def _populate(self) -> None:
        candidates = [e for e in self.ctx.demo_students if e.intended_condition is None]
        self.table.setRowCount(len(candidates))
        for row, entry in enumerate(candidates):
            student = entry.student
            self.table.setItem(row, 0, QTableWidgetItem(student.name))
            self.table.setItem(row, 1, QTableWidgetItem(student.class_name))
            current_pen = "ND"
            if student.pen_row is not None:
                current_pen = self.ctx.sheets.get_row_values(student.pen_row).get("PEN", "ND")
            self.table.setItem(row, 2, QTableWidgetItem(current_pen))

            btn = QPushButton("Check now")
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _checked, sid=student.student_id: self._run(sid))
            wrap = QWidget()
            wrap_layout = QHBoxLayout(wrap)
            wrap_layout.setContentsMargins(4, 4, 4, 4)
            wrap_layout.addWidget(btn)
            self.table.setCellWidget(row, 3, wrap)

    def _run(self, student_id: str) -> None:
        if self.worker is not None:
            return
        entry = next(
            (e for e in self.ctx.demo_students if e.student.student_id == student_id), None
        )
        if entry is None:
            return
        self.status_label.setText(f"Checking {entry.student.name}…")
        self.worker = _NdReconciliationWorker(
            self.ctx.settings.sqlite_path, self.ctx.sheets, entry.student, entry.student.class_name,
        )
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_thread_finished)
        self.worker.start()

    def _on_finished(self, outcome: str) -> None:
        self.status_label.setText(f"Outcome: {outcome}")
        self._populate()

    def _on_failed(self, message: str) -> None:
        self.status_label.setText(f"Check failed: {message}")

    def _on_thread_finished(self) -> None:
        self.worker = None
