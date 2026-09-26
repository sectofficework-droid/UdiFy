"""Persists LIVE-mode configuration edited through the Settings screen
back into `.env`/`credentials/` — the same files SETUP-GUIDE.md already
documents as the source of configuration (src/config/settings.py).

Never logs the values it writes (RULEBOOK.md §J6/§L8) — only file paths
and key *names* ever appear in any message here. Deliberately does NOT
touch `UDIFY_ENVIRONMENT` — switching into LIVE mode stays a separate,
deliberate edit (SETUP-GUIDE.md), never a side effect of saving Google
Sheets/portal configuration through this screen.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from src.config.settings import PROJECT_ROOT


def write_env_values(values: dict[str, str], env_file: Path | None = None) -> None:
    """Updates/adds the given key=value pairs in the .env file, preserving
    every other line (comments, unrelated keys) untouched. Creates the
    file from .env.example if it doesn't exist yet. A value of "" clears
    that key to empty (still written, not removed) rather than silently
    keeping a stale credential around.
    """
    path = env_file or (PROJECT_ROOT / ".env")
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        example = PROJECT_ROOT / ".env.example"
        lines = example.read_text(encoding="utf-8").splitlines() if example.exists() else []

    remaining = dict(values)
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}")
                continue
        new_lines.append(line)
    for key, value in remaining.items():
        new_lines.append(f"{key}={value}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def import_service_account_file(source: Path, dest_dir: Path | None = None) -> Path:
    """Copies a chosen Google service-account JSON key into the project's
    git-ignored `credentials/` folder and returns its absolute path (to be
    stored as GOOGLE_SERVICE_ACCOUNT_FILE) — never left referencing a file
    outside that folder, since only `credentials/` is git-ignored."""
    target_dir = dest_dir or (PROJECT_ROOT / "credentials")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "service-account.json"
    shutil.copyfile(source, target)
    return target.resolve()
