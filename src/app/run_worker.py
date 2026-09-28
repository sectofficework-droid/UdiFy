"""Background worker: runs a Condition*Engine inside a QThread, so
Playwright/SQLite calls never block the GUI event loop.

Opens its OWN SQLite connection to the same database file rather than
reusing AppContext.conn — Python's sqlite3 connections are not safe to
share across threads (spec-agnostic Python constraint, not a business
rule).

Which portals it drives is decided entirely by `portal_factory`, from the
same `Settings` the rest of the app uses — the real government portals at
their configured login URLs. Before 2026-09-27 this file hardcoded local
mock-page paths and passed `environment="MOCK"` as a literal, so a
LIVE-configured app silently ran against mock pages while writing to the
real spreadsheets.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from playwright.sync_api import sync_playwright

from src.app.app_context import AppContext, DemoStudentEntry
from src.app.portal_factory import PortalSession, open_portal_session
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
        session: PortalSession | None = None
        try:
            environment = self.ctx.settings.environment.value
            with sync_playwright() as pw:
                # Never headless, in either environment (spec's
                # "visible/headed browser operation" criterion).
                browser = pw.chromium.launch(headless=False)
                try:
                    self.progress.emit(
                        "Opening portals (visible — never headless): "
                        "REAL government portals..."
                    )
                    session, _ = open_portal_session(self.ctx.settings, browser)

                    student = self.entry.student
                    self.progress.emit(
                        f"Determining entry condition for {student.name} from sheet "
                        "state (spec §78 DETERMINE_ENTRY_CONDITION)..."
                    )
                    result = run_entry(
                        self.ctx.sheets,
                        session.gujarat,
                        session.national,
                        conn,
                        student,
                        environment=environment,
                    )
                    if result is None:
                        self.progress.emit(
                            f"{student.name} is already complete on both sides "
                            "(spec §264) — nothing to run."
                        )

                    self.finished_ok.emit(result)
                finally:
                    if session is not None:
                        session.close()
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

