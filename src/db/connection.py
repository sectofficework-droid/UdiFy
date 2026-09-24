"""SQLite connection helper."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.db.schema import initialize_database


def connect(path: Path | str) -> sqlite3.Connection:
    """Open (creating if needed) the UdiFy SQLite database, schema applied."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    return conn
