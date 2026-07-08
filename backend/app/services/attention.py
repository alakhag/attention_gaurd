from uuid import uuid4
from app.db import db, now_iso
from app.services.classifier import classify_text

def insert_and_classify(source, source_item_id, account_email=None, device_id=None, package_name=None,
                        app_name=None, sender=None, title=None, body=None, timestamp=None):
    item_id = f"item_{uuid4().hex}"
    class_id = f"class_{uuid4().hex}"
    created = now_iso()
    timestamp = timestamp or created

    with db() as conn:
        existing = conn.execute("SELECT id FROM items WHERE source_item_id = ?", (source_item_id,)).fetchone()
        if existing:
            return {"deduped": True, "item_id": existing["id"]}

        conn.execute("""
            INSERT INTO items (id, source, source_item_id, account_email, device_id, package_name, app_name,
                               sender, title, body, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, source, source_item_id, account_email, device_id, package_name, app_name,
              sender, title, body, timestamp, created))

    c = classify_text(source, app_name, sender, title, body)

    attn_id = None
    with db() as conn:
        conn.execute("""
            INSERT INTO classifications (id, item_id, needs_attention, category, urgency, confidence, reason, recommended_action, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (class_id, item_id, 1 if c.needs_attention else 0, c.category, c.urgency,
              c.confidence, c.reason, c.recommended_action, created))

        if c.needs_attention:
            attn_id = f"attn_{uuid4().hex}"
            conn.execute("""
                INSERT INTO attention_items (id, item_id, status, surfaced_at)
                VALUES (?, ?, 'active', ?)
            """, (attn_id, item_id, created))

    return {
        "deduped": False,
        "item_id": item_id,
        "attention_item_id": attn_id,
        "classification": c.model_dump(),
        "final_status": "needs_attention" if attn_id else "not_attention",
        "notify_user": bool(attn_id),
    }

def get_status():
    items = list_attention_items()
    count = len(items)
    with db() as conn:
        last = conn.execute("SELECT MAX(created_at) AS last_checked_at FROM items").fetchone()
        last_checked_at = last["last_checked_at"] if last and last["last_checked_at"] else None

    if count == 0:
        return {
            "status": "clear",
            "attention_count": 0,
            "summary": "Nothing important missed",
            "top_items": [],
            "last_checked_at": last_checked_at,
        }

    top = [f"{x['title'] or x['app_name'] or x['source']}: {x['recommended_action']}" for x in items[:3]]
    return {
        "status": "needs_attention",
        "attention_count": count,
        "summary": f"{count} {'thing needs' if count == 1 else 'things need'} attention",
        "top_items": top,
        "last_checked_at": last_checked_at,
    }

def list_attention_items():
    with db() as conn:
        rows = conn.execute("""
            SELECT
                ai.id AS attention_id, ai.status, ai.surfaced_at,
                i.id AS item_id, i.source, i.account_email, i.device_id, i.package_name, i.app_name,
                i.sender, i.title, i.body, i.timestamp,
                c.category, c.urgency, c.confidence, c.reason, c.recommended_action
            FROM attention_items ai
            JOIN items i ON i.id = ai.item_id
            JOIN classifications c ON c.item_id = i.id
            WHERE ai.status = 'active'
            ORDER BY ai.surfaced_at DESC
        """).fetchall()
    return [dict(r) for r in rows]

def set_attention_status(attention_id, status):
    field = "resolved_at" if status == "resolved" else "dismissed_at"
    with db() as conn:
        cur = conn.execute(
            f"UPDATE attention_items SET status = ?, {field} = ? WHERE id = ?",
            (status, now_iso(), attention_id)
        )
    return cur.rowcount > 0

def phone_payload():
    status = get_status()
    items = list_attention_items()
    return {
        "summary": status["summary"],
        "status": status["status"],
        "attention_count": status["attention_count"],
        "last_checked_at": status.get("last_checked_at"),
        "items": [
            {
                "id": x["attention_id"],
                "title": x["title"] or x["sender"] or x["app_name"] or x["source"],
                "body": x["body"] or x["reason"],
                "source": x["source"],
                "category": x["category"],
                "urgency": x["urgency"],
                "reason": x["reason"],
                "recommended_action": x["recommended_action"],
            }
            for x in items[:10]
        ]
    }
