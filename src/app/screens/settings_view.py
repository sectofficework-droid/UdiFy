"""Settings (UI-SPEC.md §B.1): configure the Google Sheets connection and
portal logins through the GUI instead of hand-editing `.env` each time —
never displays a previously-saved secret back in plain text (RULEBOOK.md
§J6/§L8), and never logs a value entered here.

Editable for the Google Sheets connection (service-account key + the
three spreadsheet IDs — OGR/UDISE/PEN stay the confirmed, fixed sheet
roles; only WHICH spreadsheet each points to is dynamic) and both portal
logins. `UDIFY_ENVIRONMENT` itself stays read-only here deliberately —
flipping into LIVE mode is a separate, explicit edit (SETUP-GUIDE.md),
never a side effect of saving this form.

Saving writes to `.env`/`credentials/` (both already git-ignored) via
src/config/settings_writer.py and takes effect on the next app restart —
this screen does not attempt to hot-swap the running AppContext's
settings mid-session.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.app.app_context import AppContext
from src.app.widgets import screen_header
from src.config.settings_writer import import_service_account_file, write_env_values


class SettingsScreen(QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        settings = ctx.settings
        self._service_account_path: str = settings.sheets.service_account_file or ""

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(
            screen_header(
                "Settings",
                "Google Sheets connection and portal logins — saved to .env/"
                "credentials/ (both git-ignored) and applied on next restart.",
            )
        )

        # This form has enough rows that, at some window heights (a
        # maximized window is shorter than you'd expect once the taskbar
        # is subtracted), the content doesn't fit and Qt was silently
        # compressing every row toward its minimum size instead of
        # showing a scrollbar — squeezing rows below the height text
        # rendering needs cleanly, which showed up as vertically clipped
        # placeholder text. A QScrollArea keeps every row at its natural
        # height regardless of window size; if it doesn't fit, it
        # scrolls, which is what should have been happening all along.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll, stretch=1)

        info_panel = QFrame()
        info_panel.setObjectName("Panel")
        info_form = QFormLayout(info_panel)
        info_form.setContentsMargins(16, 14, 16, 14)
        info_form.setSpacing(10)
        info_form.addRow("Environment", QLabel(settings.environment.value))
        info_form.addRow("SQLite database", QLabel(str(settings.sqlite_path)))
        info_form.addRow("Diagnostics directory", QLabel(str(settings.diagnostics_dir)))
        info_form.addRow("Log level", QLabel(settings.log_level))
        layout.addWidget(info_panel)

        panel = QFrame()
        panel.setObjectName("Panel")
        form = QFormLayout(panel)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(10)

        form.addRow(QLabel("<b>Google Sheets</b>"), QLabel(""))

        sa_row = QHBoxLayout()
        sa_row.setContentsMargins(0, 0, 0, 0)
        # A read-only QLineEdit, not a word-wrapped QLabel: a wrapping
        # QLabel nested in a QHBoxLayout inside a QFormLayout row doesn't
        # reliably compute its own height (Qt height-for-width doesn't
        # propagate through that nesting) — it can collapse to a few
        # pixels tall while still trying to paint full-height text,
        # rendering as garbled/overlapping glyphs. A QLineEdit has a
        # fixed single-line height regardless of content, sidestepping
        # the whole problem, and its text stays selectable/copyable.
        self.service_account_label = QLineEdit(
            self._service_account_path or "— not configured —"
        )
        self.service_account_label.setReadOnly(True)
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("Secondary")
        browse_btn.clicked.connect(self._browse_service_account)
        sa_row.addWidget(self.service_account_label, stretch=1)
        sa_row.addWidget(browse_btn)
        sa_wrap = QWidget()
        sa_wrap.setLayout(sa_row)
        # A custom composite widget (QWidget + manual QHBoxLayout) sitting
        # in a QFormLayout row doesn't reliably get a correct sizeHint
        # once the row stretches very wide (e.g. a maximized window) —
        # both children's geometry could collapse/miscalculate, which is
        # what was rendering as garbled text and a malformed "Browse…"
        # button. Pinning the wrapper to its children's natural single-
        # line height removes the ambiguity Qt was getting wrong; nothing
        # here actually needs a dynamic height.
        sa_wrap.setFixedHeight(self.service_account_label.sizeHint().height())
        form.addRow("Service account key (.json)", sa_wrap)

        self.ogr_id = QLineEdit(settings.sheets.spreadsheet_id_ogr or "")
        self.ogr_id.setPlaceholderText("Spreadsheet ID from the OGR sheet's URL")
        form.addRow("OGR spreadsheet ID", self.ogr_id)

        self.udise_id = QLineEdit(settings.sheets.spreadsheet_id_udise or "")
        self.udise_id.setPlaceholderText("Spreadsheet ID from the UDISE sheet's URL")
        form.addRow("UDISE spreadsheet ID", self.udise_id)

        self.pen_id = QLineEdit(settings.sheets.spreadsheet_id_pen or "")
        self.pen_id.setPlaceholderText("Spreadsheet ID from the PEN sheet's URL")
        form.addRow("PEN spreadsheet ID", self.pen_id)

        form.addRow(QLabel(""), QLabel(""))
        form.addRow(QLabel("<b>Gujarat UDISE portal</b>"), QLabel(""))
        self.gujarat_login_url = QLineEdit(settings.gujarat_portal.login_url or "")
        self.gujarat_login_url.setPlaceholderText("https://...")
        form.addRow("Login URL", self.gujarat_login_url)
        self.gujarat_school_code = QLineEdit(settings.gujarat_portal.school_code or "")
        form.addRow("School code", self.gujarat_school_code)
        self.gujarat_username = QLineEdit(settings.gujarat_portal.username or "")
        form.addRow("Username", self.gujarat_username)
        self.gujarat_password = QLineEdit()
        self.gujarat_password.setEchoMode(QLineEdit.Password)
        self.gujarat_password.setPlaceholderText(
            "— already saved, leave blank to keep —" if settings.gujarat_portal.password else ""
        )
        form.addRow("Password", self.gujarat_password)

        form.addRow(QLabel(""), QLabel(""))
        form.addRow(QLabel("<b>National UDISE+ portal</b>"), QLabel(""))
        self.national_login_url = QLineEdit(settings.national_portal.login_url or "")
        self.national_login_url.setPlaceholderText("https://...")
        form.addRow("Login URL", self.national_login_url)
        self.national_username = QLineEdit(settings.national_portal.username or "")
        form.addRow("Username", self.national_username)
        self.national_password = QLineEdit()
        self.national_password.setEchoMode(QLineEdit.Password)
        self.national_password.setPlaceholderText(
            "— already saved, leave blank to keep —" if settings.national_portal.password else ""
        )
        form.addRow("Password", self.national_password)

        layout.addWidget(panel)

        save_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        save_row.addWidget(self.save_btn)
        save_row.addStretch(1)
        layout.addLayout(save_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch(1)

        self._existing_gujarat_password = settings.gujarat_portal.password or ""
        self._existing_national_password = settings.national_portal.password or ""

    def _browse_service_account(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Google service-account key", "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            imported = import_service_account_file(Path(path))
        except OSError as exc:
            self.status_label.setText(f"⚠ Could not copy the key file: {exc}")
            return
        self._service_account_path = str(imported)
        self.service_account_label.setText(self._service_account_path)

    def _save(self) -> None:
        # A blank password field means "keep whatever was already saved" —
        # never overwrite a real credential with an accidental empty value
        # just because the operator didn't retype it.
        gujarat_password = self.gujarat_password.text() or self._existing_gujarat_password
        national_password = self.national_password.text() or self._existing_national_password

        write_env_values({
            "GOOGLE_SERVICE_ACCOUNT_FILE": self._service_account_path,
            "GOOGLE_SPREADSHEET_ID_OGR": self.ogr_id.text().strip(),
            "GOOGLE_SPREADSHEET_ID_UDISE": self.udise_id.text().strip(),
            "GOOGLE_SPREADSHEET_ID_PEN": self.pen_id.text().strip(),
            "GUJARAT_UDISE_LOGIN_URL": self.gujarat_login_url.text().strip(),
            "GUJARAT_UDISE_SCHOOL_CODE": self.gujarat_school_code.text().strip(),
            "GUJARAT_UDISE_USERNAME": self.gujarat_username.text().strip(),
            "GUJARAT_UDISE_PASSWORD": gujarat_password,
            "NATIONAL_UDISE_PLUS_LOGIN_URL": self.national_login_url.text().strip(),
            "NATIONAL_UDISE_PLUS_USERNAME": self.national_username.text().strip(),
            "NATIONAL_UDISE_PLUS_PASSWORD": national_password,
        })

        self._existing_gujarat_password = gujarat_password
        self._existing_national_password = national_password
        self.gujarat_password.clear()
        self.national_password.clear()
        self.gujarat_password.setPlaceholderText(
            "— already saved, leave blank to keep —" if gujarat_password else ""
        )
        self.national_password.setPlaceholderText(
            "— already saved, leave blank to keep —" if national_password else ""
        )

        self.status_label.setText(
            "✓ Saved to .env — restart UdiFy for these changes to take effect. "
            "Environment stays MOCK until UDIFY_ENVIRONMENT is changed separately."
        )
