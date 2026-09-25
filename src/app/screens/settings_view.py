"""Settings (UI-SPEC.md §B.1): where the operator sees the Google Sheets
connection and portal login configuration — never displays or logs secret
values in plain text (RULEBOOK.md §J6/§L8).

Read-only for this build: real credential entry through the GUI is
explicitly deferred to the Live Verification Gate phase (TODO.md step 17)
— editing them here now, before that gate, would risk exactly what the
mock-first decision exists to prevent (a GUI-entered credential being
used against a real portal before the gate's controlled checks). Values
are configured via `.env` per SETUP-GUIDE.md.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QVBoxLayout, QWidget

from src.app.app_context import AppContext
from src.app.widgets import screen_header


def _mask(value: str | None) -> str:
    if not value:
        return "— not configured —"
    return "•" * max(len(value), 6)


class SettingsScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        settings = ctx.settings

        layout = QVBoxLayout(self)
        layout.addWidget(
            screen_header(
                "Settings",
                "Configured via .env (see SETUP-GUIDE.md) — never edited here "
                "before the Live Verification Gate.",
            )
        )

        panel = QFrame()
        panel.setObjectName("Panel")
        form = QFormLayout(panel)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(10)

        form.addRow("Environment", QLabel(settings.environment.value))
        form.addRow("SQLite database", QLabel(str(settings.sqlite_path)))
        form.addRow("Diagnostics directory", QLabel(str(settings.diagnostics_dir)))
        form.addRow("Log level", QLabel(settings.log_level))

        form.addRow(QLabel(""), QLabel(""))
        form.addRow(QLabel("<b>Google Sheets</b>"), QLabel(""))
        form.addRow("Service account file", QLabel(
            settings.sheets.service_account_file or "— not configured —"
        ))
        form.addRow("OGR spreadsheet ID", QLabel(settings.sheets.spreadsheet_id_ogr or "— not configured —"))
        form.addRow("UDISE spreadsheet ID", QLabel(settings.sheets.spreadsheet_id_udise or "— not configured —"))
        form.addRow("PEN spreadsheet ID", QLabel(settings.sheets.spreadsheet_id_pen or "— not configured —"))

        form.addRow(QLabel(""), QLabel(""))
        form.addRow(QLabel("<b>Gujarat UDISE portal</b>"), QLabel(""))
        form.addRow("School code", QLabel(settings.gujarat_portal.school_code or "— not configured —"))
        form.addRow("Username", QLabel(settings.gujarat_portal.username or "— not configured —"))
        form.addRow("Password", QLabel(_mask(settings.gujarat_portal.password)))

        form.addRow(QLabel(""), QLabel(""))
        form.addRow(QLabel("<b>National UDISE+ portal</b>"), QLabel(""))
        form.addRow("Username", QLabel(settings.national_portal.username or "— not configured —"))
        form.addRow("Password", QLabel(_mask(settings.national_portal.password)))

        layout.addWidget(panel)
        layout.addStretch(1)
