"""
SQLite database setup for score history.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# DB path relative to where app runs
DB_PATH = os.environ.get(
    "SCORES_DB_PATH",
    str(Path.home() / ".repo_health_score" / "scores.db"),
)


def get_db_path() -> Path:
    """Return the database file path, creating parent dir if needed."""
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    """Create the scores DB and tables if they don't exist."""
    path = get_db_path()
    conn = sqlite3.connect(str(path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            repo TEXT NOT NULL,
            overall_score REAL NOT NULL,
            overall_letter TEXT NOT NULL,
            dimensions_json TEXT NOT NULL,
            scanned_at TEXT NOT NULL,
            UNIQUE(owner, repo, scanned_at)
        )
    """)
    conn.commit()
    conn.close()


@contextmanager
def get_connection():
    """Context manager for DB connections."""
    path = get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def store_score(
    owner: str,
    repo: str,
    overall_score: float,
    overall_letter: str,
    dimensions_json: str,
    scanned_at: str,
) -> int:
    """Store a score in the history table. Returns the row id.

    Uses INSERT OR REPLACE so duplicate scans (same owner/repo/scanned_at)
    overwrite the previous entry instead of silently dropping it.
    Returns 0 if the write failed for any reason.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO score_history
                (owner, repo, overall_score, overall_letter, dimensions_json, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (owner, repo, overall_score, overall_letter, dimensions_json, scanned_at))
        conn.commit()
        return cursor.lastrowid if cursor.lastrowid else 0


def get_history(
    owner: str,
    repo: str,
    days: Optional[int] = None,
) -> list[dict]:
    """Get score history for a repo, optionally filtered by days."""
    # days=0 means "no history" — return empty immediately
    if days is not None and days <= 0:
        return []

    with get_connection() as conn:
        cursor = conn.cursor()
        if days is not None:
            cursor.execute("""
                SELECT * FROM score_history
                WHERE owner = ? AND repo = ?
                AND datetime(scanned_at) >= datetime('now', '-' || ? || ' days')
                ORDER BY scanned_at DESC
            """, (owner, repo, days))
        else:
            cursor.execute("""
                SELECT * FROM score_history
                WHERE owner = ? AND repo = ?
                ORDER BY scanned_at DESC
            """, (owner, repo))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_latest_score(owner: str, repo: str) -> Optional[dict]:
    """Get the most recent score for a repo."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM score_history
            WHERE owner = ? AND repo = ?
            ORDER BY scanned_at DESC
            LIMIT 1
        """, (owner, repo))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_repos(limit: int = 100) -> list[dict]:
    """
    Get the most recent score entry for each unique repo in the database.
    Ordered by overall_score ascending (worst first).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM score_history s1
            WHERE scanned_at = (
                SELECT MAX(scanned_at)
                FROM score_history s2
                WHERE s2.owner = s1.owner AND s2.repo = s1.repo
            )
            ORDER BY overall_score ASC, owner ASC, repo ASC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]