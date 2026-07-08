import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "./attention_guard.db")


def ensure_db_dir():
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def db():
    ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            device_id TEXT,
            package_name TEXT,
            app_name TEXT,
            title TEXT,
            body TEXT,
            notification_key TEXT,
            timestamp TEXT,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            needs_attention INTEGER NOT NULL,
            category TEXT NOT NULL,
            urgency TEXT NOT NULL,
            confidence REAL NOT NULL,
            reason TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS attention_items (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            status TEXT NOT NULL,
            surfaced_at TEXT NOT NULL,
            dismissed_at TEXT,
            resolved_at TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS corrections (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            correction TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """)
        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_items_notification_key
        ON items(notification_key)
        """)
