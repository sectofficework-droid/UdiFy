"""Resolves the MOCK portal fixture pages' location — from the source
tree during development, or from PyInstaller's bundle directory once
packaged (spec decision: mock-first, so the shipped MOCK-mode demo must
keep working from a packaged .exe too, not just `pytest`)."""

from __future__ import annotations

import sys
from pathlib import Path


def fixtures_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "fixtures"
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures"


GUJARAT_FIXTURE = fixtures_root() / "gujarat_udise" / "new_entry.html"
NATIONAL_FIXTURE = fixtures_root() / "udise_plus" / "new_pen_entry.html"
