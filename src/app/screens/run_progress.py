"""Run & Progress (UI-SPEC.md §B.1): per-student progress through the
state machine, live status, pause/manual-intervention indicator.

The state-machine "stepper" is populated from the real `pen_case_events`
audit trail once a run completes/pauses — not simulated — since that
table is this project's actual source of truth for what happened.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_context import AppContext, DemoStudentEntry
from src.app.run_worker import RunWorker
from src.app.widgets import screen_header, status_chip
from src.db.events import get_case_history


class RunProgressScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.worker: RunWorker | None = None
        self.current_entry: DemoStudentEntry | None = None

        layout = QVBoxLayout(self)
        self.header = screen_header("Run & Progress", "Select a student from Batch Queue.")
        layout.addWidget(self.header)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start run")
        self.start_btn.clicked.connect(self._start)
        self.start_btn.setEnabled(False)
        controls.addWidget(self.start_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        layout.addWidget(self.banner)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        layout.addWidget(self.log_view)

        self.stepper = QTableWidget(0, 4)
        self.stepper.setHorizontalHeaderLabels(["Event", "Status after", "Portal status", "Note"])
        self.stepper.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.stepper.verticalHeader().setVisible(False)
        self.stepper.verticalHeader().setDefaultSectionSize(32)
        self.stepper.horizontalHeader().resizeSection(0, 220)
        self.stepper.horizontalHeader().resizeSection(1, 150)
        layout.addWidget(self.stepper, stretch=1)

    def load_student(self, student_id: str) -> None:
        entry = next(
            (e for e in self.ctx.demo_students if e.student.student_id == student_id), None
        )
        self.current_entry = entry
        self.log_view.clear()
        self.banner.setVisible(False)
        self.stepper.setRowCount(0)
        if entry is None:
            self.start_btn.setEnabled(False)
            return
        self.start_btn.setEnabled(entry.intended_condition is not None)
        self._append_log(
            f"Loaded {entry.student.name} — {entry.note}"
            + ("" if entry.intended_condition else " (use ND Reconciliation screen instead)")
        )
        self._refresh_stepper()

    def _append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def _start(self) -> None:
        if self.current_entry is None or self.worker is not None:
            return
        self.start_btn.setEnabled(False)
        self.banner.setVisible(False)
        self._append_log("— starting run —")
        self.worker = RunWorker(self.ctx, self.current_entry)
        self.worker.progress.connect(self._append_log)
        self.worker.paused.connect(self._on_paused)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_thread_finished)
        self.worker.start()

    def _on_paused(self, reason: str, checkpoint: str) -> None:
        self._append_log(f"PAUSED FOR OPERATOR: {reason} (checkpoint: {checkpoint})")
        self.banner.setText(
            f"⏸ Manual intervention required: {reason}\nCheckpoint: {checkpoint} — "
            "this is a deliberate, expected pause (spec §I), not an error. The "
            "operator completes the step in the browser window, then resumes."
        )
        self.banner.setVisible(True)

    def _on_finished(self, result: object) -> None:
        self._append_log(f"Finished: {result}")
        self._refresh_stepper()

    def _on_failed(self, message: str) -> None:
        self._append_log(f"FAILED: {message}")
        self.banner.setText(f"⚠ Run failed: {message}")
        self.banner.setVisible(True)
        self._refresh_stepper()

    def _on_thread_finished(self) -> None:
        self.worker = None
        self.start_btn.setEnabled(
            self.current_entry is not None and self.current_entry.intended_condition is not None
        )

    def _refresh_stepper(self) -> None:
        self.stepper.setRowCount(0)
        if self.current_entry is None:
            return
        history = get_case_history(self.ctx.conn, self.current_entry.student.student_id)
        self.stepper.setRowCount(len(history))
        for row, event in enumerate(history):
            self.stepper.setItem(row, 0, QTableWidgetItem(event["event_code"]))
            self.stepper.setCellWidget(row, 1, status_chip(event["case_status_after"]))
            self.stepper.setItem(row, 2, QTableWidgetItem(event["portal_status"] or ""))
            note = event["resolution_note"] or event["reopen_reason"] or ""
            self.stepper.setItem(row, 3, QTableWidgetItem(note))
