"""SQLite database for run history."""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("FLAMELET_DB", "~/.local/share/flamelet/runs.db")).expanduser()


def get_conn():
    """Get SQLite connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                tenant TEXT,
                task TEXT,
                hosts TEXT,
                status TEXT DEFAULT 'queued',
                dry_run INTEGER DEFAULT 1,
                started_at REAL,
                finished_at REAL
            );
            CREATE TABLE IF NOT EXISTS run_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT REFERENCES runs(id),
                ts REAL,
                line TEXT
            );
        """
        )


def insert_run(run_id, tenant, task, hosts, dry_run=True):
    """Insert a new run record."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (id, tenant, task, hosts, dry_run, status) VALUES (?, ?, ?, ?, ?, 'queued')",
            (run_id, tenant, task, ",".join(hosts), int(dry_run)),
        )


def update_run_status(run_id, status, started_at=None, finished_at=None):
    """Update run status."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE runs SET status=?, started_at=COALESCE(?, started_at), finished_at=? WHERE id=?",
            (status, started_at, finished_at, run_id),
        )


def insert_log(run_id, ts, line):
    """Insert a log line."""
    with get_conn() as conn:
        conn.execute("INSERT INTO run_logs (run_id, ts, line) VALUES (?, ?, ?)", (run_id, ts, line))


def get_run(run_id):
    """Get run details."""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()


def get_runs(limit=50):
    """Get recent runs."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, tenant, task, hosts, status, started_at, finished_at FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_run_logs(run_id):
    """Get all logs for a run."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, line FROM run_logs WHERE run_id=? ORDER BY id ASC", (run_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_run_logs_since(run_id, last_id=0):
    """Get logs since last_id."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, ts, line FROM run_logs WHERE run_id=? AND id>? ORDER BY id",
            (run_id, last_id),
        ).fetchall()
        return [dict(row) for row in rows]
