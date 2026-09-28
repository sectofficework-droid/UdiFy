r"""Shared helpers for the live verification scripts.

Deliberately not a pytest module — see README.md in this directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import Settings, load_settings


def require_live_settings() -> Settings:
    """Load settings, refusing to continue unless every credential is set.

    `load_settings()` already raises via `require_live_credentials()` if
    anything required is missing — these scripts always talk to the real
    portals and spreadsheets, so an incomplete `.env` must fail loudly here
    rather than let a script run against nothing.
    """
    return load_settings()


def show_config_summary(settings: Settings) -> None:
    """Print configuration facts without ever printing a secret."""
    def state(value: str | None) -> str:
        return "set" if value else "MISSING"

    print("Configuration (values deliberately not printed):")
    print(f"  environment                : {settings.environment.value}")
    print(f"  service-account file       : {state(settings.sheets.service_account_file)}")
    print(f"  spreadsheet id  OGR        : {state(settings.sheets.spreadsheet_id_ogr)}")
    print(f"  spreadsheet id  UDISE      : {state(settings.sheets.spreadsheet_id_udise)}")
    print(f"  spreadsheet id  PEN        : {state(settings.sheets.spreadsheet_id_pen)}")
    print(f"  gujarat login url          : {state(settings.gujarat_portal.login_url)}")
    print(f"  gujarat school code        : {state(settings.gujarat_portal.school_code)}")
    print(f"  gujarat username           : {state(settings.gujarat_portal.username)}")
    print(f"  gujarat password           : {state(settings.gujarat_portal.password)}")
    print(f"  national login url         : {state(settings.national_portal.login_url)}")
    print(f"  national username          : {state(settings.national_portal.username)}")
    print(f"  national password          : {state(settings.national_portal.password)}")
    print()


def banner(text: str) -> None:
    print()
    print("=" * 74)
    print(text)
    print("=" * 74)
