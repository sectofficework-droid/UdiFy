"""MainWindow: fixed sidebar nav + single content area (UI-SPEC.md §B.2
layout convention)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.app.app_context import AppContext
from src.app.screens.approval_history import ApprovalHistoryScreen
from src.app.screens.approval_monitoring import ApprovalMonitoringScreen
from src.app.screens.automation_coverage import AutomationCoverageScreen
from src.app.screens.dashboard import DashboardScreen
from src.app.screens.diagnostics_view import DiagnosticsScreen
from src.app.screens.nd_reconciliation_view import NdReconciliationScreen
from src.app.screens.run_progress import RunProgressScreen
from src.app.screens.settings_view import SettingsScreen

_NAV_ITEMS = [
    ("dashboard", "Batch Queue"),
    ("run_progress", "Run && Progress"),
    ("approval_monitoring", "Approval Monitoring"),
    ("approval_history", "Approval History"),
    ("nd_reconciliation", "ND Reconciliation"),
    ("diagnostics", "Diagnostics"),
    ("automation_coverage", "Automation Coverage"),
    ("settings", "Settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("UdiFy — UDISE/PEN Automation")
        self.resize(1280, 820)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        content_wrap = QWidget()
        content_wrap.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(28, 22, 28, 22)
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        root.addWidget(content_wrap, stretch=1)

        self.run_progress_screen = RunProgressScreen(ctx)
        self.dashboard_screen = DashboardScreen(ctx, on_run_requested=self._go_run_student)

        self.screens: dict[str, QWidget] = {
            "dashboard": self.dashboard_screen,
            "run_progress": self.run_progress_screen,
            "approval_monitoring": ApprovalMonitoringScreen(ctx),
            "approval_history": ApprovalHistoryScreen(ctx),
            "nd_reconciliation": NdReconciliationScreen(ctx),
            "diagnostics": DiagnosticsScreen(ctx),
            "automation_coverage": AutomationCoverageScreen(ctx),
            "settings": SettingsScreen(ctx),
        }
        for key, _ in _NAV_ITEMS:
            self.stack.addWidget(self.screens[key])

        self._select_nav("dashboard")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("UdiFy")
        title.setObjectName("BrandTitle")
        layout.addWidget(title)
        subtitle = QLabel(f"{self.ctx.settings.environment.value} mode")
        subtitle.setObjectName("BrandSubtitle")
        layout.addWidget(subtitle)

        self.nav_group = QButtonGroup(sidebar)
        self.nav_group.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        for key, label in _NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, k=key: self._select_nav(k))
            self.nav_group.addButton(btn)
            self._nav_buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)
        return sidebar

    def _select_nav(self, key: str) -> None:
        self._nav_buttons[key].setChecked(True)
        self.stack.setCurrentWidget(self.screens[key])
        refresh = getattr(self.screens[key], "on_shown", None)
        if callable(refresh):
            refresh()

    def _go_run_student(self, student_id: str) -> None:
        self.run_progress_screen.load_student(student_id)
        self._select_nav("run_progress")
