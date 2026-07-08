from uuid import uuid4
from datetime import datetime, timezone
import sqlite3

from app.db import db
from app.models import AndroidNotificationIn
from app.services.classifier import classify_notification


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def ingest_notification(n: AndroidNotificationIn) -> dict:
    item_id = f"item_{uuid4().hex}"
    class_id = f"class_{uuid4().hex}"
    attn_id = None

    ts = n.timestamp.isoformat() if n.timestamp else iso_now()
    created = iso_now()

    classification = classify_notification(n)

    with db() as conn:
        try:
            conn.execute(
                """
                INSERT INTO items (
                    id, source, device_id, package_name, app_name,
                    title, body, notification_key, timestamp, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id, "android_notification", n.device_id, n.package_name, n.app_name,
                    n.title, n.body, n.notification_key, ts, created
                )
            )
        except sqlite3.IntegrityError:
            existing = conn.execute(
                "SELECT id FROM items WHERE notification_key = ?",
                (n.notification_key,)
            ).fetchone()
            return {
                "deduped": True,
                "item_id": existing["id"] if existing else None,
                "final_status": "duplicate",
                "notify_user": False,
            }

        conn.execute(
            """
            INSERT INTO classifications (
                id, item_id, needs_attention, category, urgency,
                confidence, reason, recommended_action, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                class_id, item_id, 1 if classification.needs_attention else 0,
                classification.category, classification.urgency, classification.confidence,
                classification.reason, classification.recommended_action, created
            )
        )

        if classification.needs_attention:
            attn_id = f"attn_{uuid4().hex}"
            conn.execute(
                """
                INSERT INTO attention_items (
                    id, item_id, status, surfaced_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (attn_id, item_id, "active", created)
            )

    return {
        "deduped": False,
        "item_id": item_id,
        "attention_item_id": attn_id,
        "final_status": "needs_attention" if attn_id else "not_attention",
        "notify_user": bool(attn_id),
        "classification": classification.model_dump(),
    }


def get_status() -> dict:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT ai.id, i.app_name, i.title, i.body, c.category, c.recommended_action, ai.surfaced_at
            FROM attention_items ai
            JOIN items i ON i.id = ai.item_id
            JOIN classifications c ON c.item_id = i.id
            WHERE ai.status = 'active'
            ORDER BY ai.surfaced_at DESC
            """
        ).fetchall()

        last = conn.execute("SELECT MAX(created_at) AS last_checked_at FROM items").fetchone()
        last_checked_at = last["last_checked_at"] if last and last["last_checked_at"] else None

    count = len(rows)
    if count == 0:
        return {
            "status": "clear",
            "attention_count": 0,
            "summary": "Nothing important missed",
            "top_items": [],
            "last_checked_at": last_checked_at,
        }

    top_items = []
    for r in rows[:3]:
        label = f"{r['title'] or r['app_name']}: {r['recommended_action']}"
        top_items.append(label)

    return {
        "status": "needs_attention",
        "attention_count": count,
        "summary": f"{count} {'thing needs' if count == 1 else 'things need'} attention",
        "top_items": top_items,
        "last_checked_at": last_checked_at,
    }


def list_attention_items() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                ai.id AS attention_id,
                ai.status,
                ai.surfaced_at,
                i.id AS item_id,
                i.source,
                i.device_id,
                i.package_name,
                i.app_name,
                i.title,
                i.body,
                i.notification_key,
                i.timestamp,
                c.needs_attention,
                c.category,
                c.urgency,
                c.confidence,
                c.reason,
                c.recommended_action
            FROM attention_items ai
            JOIN items i ON i.id = ai.item_id
            JOIN classifications c ON c.item_id = i.id
            WHERE ai.status = 'active'
            ORDER BY ai.surfaced_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def update_attention_status(attention_id: str, status: str) -> bool:
    field = "dismissed_at" if status == "dismissed" else "resolved_at"
    with db() as conn:
        cur = conn.execute(
            f"UPDATE attention_items SET status = ?, {field} = ? WHERE id = ?",
            (status, iso_now(), attention_id)
        )
    return cur.rowcount > 0


def list_items(limit: int = 100) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT i.*, c.needs_attention, c.category, c.urgency, c.confidence, c.reason, c.recommended_action
            FROM items i
            LEFT JOIN classifications c ON c.item_id = i.id
            ORDER BY i.created_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
