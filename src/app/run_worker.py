"""Background worker: runs a Condition*Engine against the MOCK fixture
portals inside a QThread, so Playwright/SQLite calls never block the GUI
event loop.

Opens its OWN SQLite connection to the same database file rather than
reusing AppContext.conn — Python's sqlite3 connections are not safe to
share across threads (spec-agnostic Python constraint, not a business
rule) — and drives the MOCK fixture pages the integration tests also use,
in a visible (never headless) browser, per spec's "Visible/headed browser
operation" acceptance criterion.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright

from src.app.app_context import AppContext, DemoStudentEntry
from src.app.mock_fixtures import GUJARAT_FIXTURE, NATIONAL_FIXTURE
from src.db.connection import connect
from src.engine.entry_router import AmbiguousEntryConditionError, run_entry
from src.engine.resilience import BrowserOrNetworkFailureError, RecoverableAutomationError
from src.portals.base import AutomationPausedForUser, PortalError
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter


class RunWorker(QThread):
    progress = Signal(str)
    paused = Signal(str, str)  # reason, checkpoint
    finished_ok = Signal(object)  # the ConditionXResult
    failed = Signal(str)

    def __init__(self, ctx: AppContext, entry: DemoStudentEntry):
        super().__init__()
        self.ctx = ctx
        self.entry = entry

    def run(self) -> None:  # noqa: overrides QThread.run — intentional
        conn = connect(self.ctx.settings.sqlite_path)
        try:
            self.progress.emit("Launching MOCK browser (visible — never headless)…")
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

                    student = self.entry.student
                    self.progress.emit(
                        f"Determining entry condition for {student.name} from sheet "
                        "state (spec §78 DETERMINE_ENTRY_CONDITION)…"
                    )
                    result = run_entry(
                        self.ctx.sheets, gujarat, national, conn, student, environment="MOCK",
                    )
                    if result is None:
                        self.progress.emit(
                            f"{student.name} is already complete on both sides "
                            "(spec §264) — nothing to run."
                        )

                    self.finished_ok.emit(result)
                finally:
                    browser.close()
        except AutomationPausedForUser as exc:
            self.paused.emit(str(exc), exc.checkpoint)
        except AmbiguousEntryConditionError as exc:
            self.failed.emit(f"Ambiguous entry condition — manual review needed: {exc}")
        except (RecoverableAutomationError, BrowserOrNetworkFailureError) as exc:
            self.failed.emit(f"{type(exc).__name__} — {exc}")
        except PortalError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # last resort: never crash the GUI silently
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            conn.close()
