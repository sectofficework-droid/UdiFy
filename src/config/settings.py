"""Application configuration.

Loads .env (never committed — see .env.example) and exposes typed
settings. Default environment is MOCK; LIVE requires every credential
field to be present (spec: "CREDENTIALS, MOCKING AND LIVE VERIFICATION
DECISION" §1/§3/§6 in UDIFY-SPECIFICATIONS.md).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Environment(str, Enum):
    MOCK = "MOCK"
    LIVE = "LIVE"


@dataclass(frozen=True)
class GoogleSheetsConfig:
    service_account_file: str | None
    spreadsheet_id_ogr: str | None
    spreadsheet_id_udise: str | None
    spreadsheet_id_pen: str | None


@dataclass(frozen=True)
class GujaratPortalCredentials:
    school_code: str | None
    username: str | None
    password: str | None


@dataclass(frozen=True)
class NationalPortalCredentials:
    username: str | None
    password: str | None


@dataclass(frozen=True)
class Settings:
    environment: Environment
    sheets: GoogleSheetsConfig
    gujarat_portal: GujaratPortalCredentials
    national_portal: NationalPortalCredentials
    diagnostics_dir: Path
    log_level: str
    sqlite_path: Path

    def require_live_credentials(self) -> None:
        """Raise if LIVE mode is requested without every required credential.

        Never silently falls back to MOCK behavior when LIVE was
        explicitly requested — that would risk a mock result being
        mistaken for a live one (spec decision §5).
        """
        if self.environment is not Environment.LIVE:
            return
        missing = []
        if not self.sheets.service_account_file:
            missing.append("GOOGLE_SERVICE_ACCOUNT_FILE")
        if not self.gujarat_portal.username or not self.gujarat_portal.password:
            missing.append("GUJARAT_UDISE_USERNAME/PASSWORD")
        if not self.national_portal.username or not self.national_portal.password:
            missing.append("NATIONAL_UDISE_PLUS_USERNAME/PASSWORD")
        if missing:
            raise RuntimeError(
                "UDIFY_ENVIRONMENT=LIVE but required credentials are missing: "
                + ", ".join(missing)
                + ". See .env.example."
            )


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings from .env (or the given path) plus process env vars.

    Never logs or returns credential values in an exception message
    beyond the field *names* above — see require_live_credentials().
    """
    load_dotenv(dotenv_path=env_file or (PROJECT_ROOT / ".env"), override=False)

    raw_env = os.environ.get("UDIFY_ENVIRONMENT", "MOCK").strip().upper()
    try:
        environment = Environment(raw_env)
    except ValueError as exc:
        raise ValueError(
            f"UDIFY_ENVIRONMENT must be MOCK or LIVE, got {raw_env!r}"
        ) from exc

    sheets = GoogleSheetsConfig(
        service_account_file=os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or None,
        spreadsheet_id_ogr=os.environ.get("GOOGLE_SPREADSHEET_ID_OGR") or None,
        spreadsheet_id_udise=os.environ.get("GOOGLE_SPREADSHEET_ID_UDISE") or None,
        spreadsheet_id_pen=os.environ.get("GOOGLE_SPREADSHEET_ID_PEN") or None,
    )
    gujarat_portal = GujaratPortalCredentials(
        school_code=os.environ.get("GUJARAT_UDISE_SCHOOL_CODE") or None,
        username=os.environ.get("GUJARAT_UDISE_USERNAME") or None,
        password=os.environ.get("GUJARAT_UDISE_PASSWORD") or None,
    )
    national_portal = NationalPortalCredentials(
        username=os.environ.get("NATIONAL_UDISE_PLUS_USERNAME") or None,
        password=os.environ.get("NATIONAL_UDISE_PLUS_PASSWORD") or None,
    )
    diagnostics_dir = PROJECT_ROOT / os.environ.get("UDIFY_DIAGNOSTICS_DIR", "diagnostics")
    log_level = os.environ.get("UDIFY_LOG_LEVEL", "INFO").strip().upper()
    sqlite_path = PROJECT_ROOT / os.environ.get("UDIFY_SQLITE_PATH", "udify.sqlite3")

    settings = Settings(
        environment=environment,
        sheets=sheets,
        gujarat_portal=gujarat_portal,
        national_portal=national_portal,
        diagnostics_dir=diagnostics_dir,
        log_level=log_level,
        sqlite_path=sqlite_path,
    )
    settings.require_live_credentials()
    return settings
