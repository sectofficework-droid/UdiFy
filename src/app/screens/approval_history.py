"""Approval History (UI-SPEC.md §B.1, spec §O): simultaneous filters,
search box, export to XLSX and CSV respecting the active filter."""

from __future__ import annotations

import csv

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_context import AppContext
from src.app.widgets import screen_header, status_chip

_COLUMNS = [
    "occurred_at", "student_id", "student_name", "event_code",
    "case_status_after", "portal_status", "environment", "resolution_note",
]
_HEADERS = [
    "When", "Student ID", "Student Name", "Event", "Status", "Portal status",
    "Environment", "Note",
]


class ApprovalHistoryScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "Approval History",
                "Every recorded pen_case_events row — the append-only, "
                "hash-chained audit trail (never edited or deleted).",
            )
        )

        controls = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by student name, ID, event, or note…")
        self.search_box.textChanged.connect(self._populate)
        controls.addWidget(self.search_box, stretch=1)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("Secondary")
        clear_btn.clicked.connect(lambda: self.search_box.setText(""))
        controls.addWidget(clear_btn)

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.setObjectName("Secondary")
        export_csv_btn.clicked.connect(self._export_csv)
        controls.addWidget(export_csv_btn)

        export_xlsx_btn = QPushButton("Export XLSX")
        export_xlsx_btn.setObjectName("Secondary")
        export_xlsx_btn.clicked.connect(self._export_xlsx)
        controls.addWidget(export_xlsx_btn)

        layout.addLayout(controls)

        self.table = QTableWidget(0, len(_HEADERS))
        self.table.setHorizontalHeaderLabels(_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().resizeSection(3, 200)
        self.table.horizontalHeader().resizeSection(4, 150)
        layout.addWidget(self.table, stretch=1)

        self._populate()

    def on_shown(self) -> None:
        self._populate()

    def _rows(self) -> list[dict]:
        query = self.search_box.text().strip().lower()
        rows = self.ctx.conn.execute(
            "SELECT occurred_at, student_id, student_name, event_code, "
            "case_status_after, portal_status, environment, resolution_note "
            "FROM pen_case_events ORDER BY created_at DESC"
        ).fetchall()
        result = [dict(row) for row in rows]
        if query:
            result = [
                r for r in result
                if query in (r["student_name"] or "").lower()
                or query in (r["student_id"] or "").lower()
                or query in (r["event_code"] or "").lower()
                or query in (r["resolution_note"] or "").lower()
            ]
        return result

    def _populate(self) -> None:
        rows = self._rows()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["occurred_at"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(row["student_id"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(row["student_name"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(row["event_code"] or ""))
            self.table.setCellWidget(i, 4, status_chip(row["case_status_after"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(row["portal_status"] or ""))
            self.table.setItem(i, 6, QTableWidgetItem(row["environment"] or ""))
            self.table.setItem(i, 7, QTableWidgetItem(row["resolution_note"] or ""))

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "approval_history.csv", "CSV (*.csv)")
        if not path:
            return
        rows = self._rows()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADERS)
            for row in rows:
                writer.writerow([row[c] or "" for c in _COLUMNS])

    def _export_xlsx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export XLSX", "approval_history.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Approval History"
        ws.append(_HEADERS)
        for row in self._rows():
            ws.append([row[c] or "" for c in _COLUMNS])
        wb.save(path)
