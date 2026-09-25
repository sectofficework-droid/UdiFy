"""Batch Queue / Dashboard (UI-SPEC.md §B.1): pick students ready for
processing, see their current condition (1-4) and status at a glance."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_context import AppContext
from src.app.widgets import StatTile, condition_chip, screen_header


class DashboardScreen(QWidget):
    def __init__(self, ctx: AppContext, on_run_requested: Callable[[str], None]):
        super().__init__()
        self.ctx = ctx
        self.on_run_requested = on_run_requested

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "Batch Queue",
                "MOCK sample data — illustrative students, not real government "
                "records. Real batches come from the configured Google Sheets "
                "once Live Verification is complete.",
            )
        )

        stats_row = QHBoxLayout()
        self.stat_total = StatTile("Total in queue")
        self.stat_ready = StatTile("Ready to run")
        self.stat_pending = StatTile("Awaiting reconciliation")
        for tile in (self.stat_total, self.stat_ready, self.stat_pending):
            stats_row.addWidget(tile)
        stats_row.addStretch(1)
        layout.addLayout(stats_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Student", "Class", "Condition", "Note", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.horizontalHeader().resizeSection(2, 130)
        self.table.horizontalHeader().resizeSection(4, 120)
        layout.addWidget(self.table, stretch=1)

        self._populate()

    def on_shown(self) -> None:
        self._populate()

    def _populate(self) -> None:
        entries = self.ctx.demo_students
        self.stat_total.set_value(str(len(entries)))
        self.stat_ready.set_value(str(sum(1 for e in entries if e.intended_condition)))
        self.stat_pending.set_value(str(sum(1 for e in entries if e.intended_condition is None)))

        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.student.name))
            self.table.setItem(row, 1, QTableWidgetItem(entry.student.class_name))
            if entry.intended_condition:
                self.table.setCellWidget(row, 2, condition_chip(entry.intended_condition))
            else:
                self.table.setItem(row, 2, QTableWidgetItem("ND reconciliation"))
            self.table.setItem(row, 3, QTableWidgetItem(entry.note))

            run_btn = QPushButton("Run" if entry.intended_condition else "Reconcile")
            run_btn.setObjectName("Secondary")
            run_btn.clicked.connect(
                lambda _checked, sid=entry.student.student_id: self.on_run_requested(sid)
            )
            wrap = QWidget()
            wrap_layout = QHBoxLayout(wrap)
            wrap_layout.setContentsMargins(4, 4, 4, 4)
            wrap_layout.addWidget(run_btn)
            self.table.setCellWidget(row, 4, wrap)
