"""Diagnostics / logs view (UI-SPEC.md §B.1, spec §H/§114): captured
screenshots and structured error context, reviewable without leaving the
app — each incident paired with a plain-language summary and a short
diagnostic ID (RULEBOOK.md §L8), never a raw stack trace."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHeaderView,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from src.app.app_context import AppContext
from src.app.widgets import screen_header, status_chip


class DiagnosticsScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "Diagnostics",
                "Every captured failure — timeout, unverified action, unknown "
                "portal state — with its diagnostic ID. Show this ID to the "
                "operator, never the raw error internals (RULEBOOK §L8).",
            )
        )

        splitter = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Diagnostic ID", "When", "Severity", "Summary", "Retry allowed"]
        )
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().resizeSection(2, 120)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.table)

        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Select a row to see full diagnostic context.")
        splitter.addWidget(self.detail)
        splitter.setSizes([320, 200])

        layout.addWidget(splitter, stretch=1)

        self._rows: list[dict] = []
        self._populate()

    def on_shown(self) -> None:
        self._populate()

    def _populate(self) -> None:
        rows = self.ctx.conn.execute(
            "SELECT diagnostic_id, occurred_at, severity, summary, retry_allowed, "
            "run_id, student_id, workflow, expected_state, observed_state, url, "
            "page_title, error_code, error_message "
            "FROM diagnostics ORDER BY occurred_at DESC"
        ).fetchall()
        self._rows = [dict(row) for row in rows]
        self.table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["diagnostic_id"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["occurred_at"] or ""))
            self.table.setCellWidget(i, 2, status_chip(row["severity"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(row["summary"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem("Yes" if row["retry_allowed"] else "No"))

    def _on_selection_changed(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows or rows[0].row() >= len(self._rows):
            self.detail.setPlainText("")
            return
        row = self._rows[rows[0].row()]
        lines = [
            f"Diagnostic ID: {row['diagnostic_id']}",
            f"Workflow: {row['workflow'] or ''}",
            f"Student: {row['student_id'] or ''}",
            f"Run ID: {row['run_id'] or ''}",
            f"Expected: {row['expected_state'] or ''}",
            f"Observed: {row['observed_state'] or ''}",
            f"URL: {row['url'] or ''}",
            f"Page title: {row['page_title'] or ''}",
            f"Error code: {row['error_code'] or ''}",
            f"Error message: {row['error_message'] or ''}",
        ]
        self.detail.setPlainText("\n".join(lines))
