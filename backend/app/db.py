import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "./attention_os.db")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def ensure_dir():
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)

@contextmanager
def db():
    ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS google_accounts (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER,
            scopes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_item_id TEXT UNIQUE,
            account_email TEXT,
            device_id TEXT,
            package_name TEXT,
            app_name TEXT,
            sender TEXT,
            title TEXT,
            body TEXT,
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attention_status ON attention_items(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_source ON items(source)")
