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

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright

from src.app.app_context import AppContext, DemoStudentEntry
from src.db.connection import connect
from src.engine.condition1 import Condition1Engine
from src.engine.condition2 import Condition2Engine
from src.engine.condition3 import Condition3Engine
from src.engine.condition4 import Condition4Engine
from src.engine.resilience import BrowserOrNetworkFailureError, RecoverableAutomationError
from src.portals.base import AutomationPausedForUser, PortalError
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter

_FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
GUJARAT_FIXTURE = _FIXTURES_ROOT / "gujarat_udise" / "new_entry.html"
NATIONAL_FIXTURE = _FIXTURES_ROOT / "udise_plus" / "new_pen_entry.html"


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
                    condition = self.entry.intended_condition
                    self.progress.emit(f"Running Condition {condition} for {student.name}…")

                    if condition == 1:
                        result = Condition1Engine(
                            self.ctx.sheets, gujarat, national, conn, "MOCK"
                        ).run(student)
                    elif condition == 2:
                        result = Condition2Engine(
                            self.ctx.sheets, gujarat, national, conn, "MOCK"
                        ).run(student)
                    elif condition == 3:
                        result = Condition3Engine(
                            self.ctx.sheets, national, conn, "MOCK"
                        ).run(student)
                    elif condition == 4:
                        result = Condition4Engine(
                            self.ctx.sheets, gujarat, national, conn, "MOCK"
                        ).run(student)
                    else:
                        raise ValueError(
                            f"No condition engine applies to {student.student_id!r} "
                            "— use ND Reconciliation instead"
                        )

                    self.finished_ok.emit(result)
                finally:
                    browser.close()
        except AutomationPausedForUser as exc:
            self.paused.emit(str(exc), exc.checkpoint)
        except (RecoverableAutomationError, BrowserOrNetworkFailureError) as exc:
            self.failed.emit(f"{type(exc).__name__} — {exc}")
        except PortalError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # last resort: never crash the GUI silently
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            conn.close()
