from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.db import init_db
from app.models import AndroidNotificationIn
from app.services.attention import (
    insert_and_classify, get_status, list_attention_items,
    set_attention_status, phone_payload
)
from app.services.google_connectors import (
    auth_url, exchange_code, connected_accounts, sync_all_google
)
import json

app = FastAPI(title="Attention OS", version="1.0")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

connections = set()

@app.on_event("startup")
def startup():
    init_db()

async def broadcast():
    payload = json.dumps({"type": "phone", "phone": phone_payload()})
    dead = []
    for ws in list(connections):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.discard(ws)

@app.get("/")
def dashboard():
    return FileResponse(static_dir / "index.html")

@app.get("/health")
def health():
    return {"ok": True, "version": "attention-os-v1"}

@app.get("/auth/google/start")
def google_start():
    return RedirectResponse(auth_url())

@app.get("/auth/google/callback")
def google_callback(code: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(f"Google auth error: {error}", status_code=400)
    if not code:
        return HTMLResponse("Missing code", status_code=400)
    email = exchange_code(code)
    return HTMLResponse(f"<h2>Connected {email}</h2><p><a href='/'>Back to Attention OS</a></p>")

@app.get("/accounts/google")
def google_accounts():
    return {"accounts": connected_accounts()}

@app.post("/sync/google")
async def sync_google():
    result = sync_all_google()
    await broadcast()
    return {"ok": True, "result": result, "phone": phone_payload()}

@app.get("/status")
def status():
    return get_status()

@app.get("/attention-items")
def attention_items():
    return {"items": list_attention_items()}

@app.get("/phone")
def phone():
    return phone_payload()

@app.post("/attention-items/{attention_id}/resolve")
async def resolve(attention_id: str):
    if not set_attention_status(attention_id, "resolved"):
        raise HTTPException(404, "attention item not found")
    await broadcast()
    return {"ok": True, "phone": phone_payload()}

@app.post("/attention-items/{attention_id}/dismiss")
async def dismiss(attention_id: str):
    if not set_attention_status(attention_id, "dismissed"):
        raise HTTPException(404, "attention item not found")
    await broadcast()
    return {"ok": True, "phone": phone_payload()}

@app.post("/android/notifications")
async def android_notifications(payload: AndroidNotificationIn):
    result = insert_and_classify(
        source="android_notification",
        source_item_id=f"android:{payload.notification_key}",
        device_id=payload.device_id,
        package_name=payload.package_name,
        app_name=payload.app_name,
        sender=payload.title,
        title=payload.title,
        body=payload.body,
        timestamp=payload.timestamp.isoformat() if payload.timestamp else None,
    )
    await broadcast()
    return {"accepted": True, "decision": result, "phone": phone_payload(), "status": get_status()}

@app.get("/debug/items")
def debug_items():
    from app.db import db
    with db() as conn:
        rows = conn.execute("""
            SELECT i.*, c.needs_attention, c.category, c.urgency, c.reason, c.recommended_action
            FROM items i LEFT JOIN classifications c ON c.item_id=i.id
            ORDER BY i.created_at DESC LIMIT 100
        """).fetchall()
    return {"items": [dict(r) for r in rows]}

@app.post("/debug/reclassify-all")
def debug_reclassify_all():
    from uuid import uuid4
    from app.db import db, now_iso
    from app.services.classifier import classify_text

    created = 0
    surfaced = 0

    with db() as conn:
        rows = conn.execute("""
            SELECT i.*
            FROM items i
            LEFT JOIN classifications c ON c.item_id = i.id
            WHERE c.id IS NULL
            ORDER BY i.created_at DESC
            LIMIT 500
        """).fetchall()

        for i in rows:
            c = classify_text(
                source=i["source"],
                app_name=i["app_name"],
                sender=i["sender"],
                title=i["title"],
                body=i["body"]
            )

            class_id = f"class_{uuid4().hex}"
            conn.execute("""
                INSERT INTO classifications
                (id, item_id, needs_attention, category, urgency, confidence, reason, recommended_action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                class_id,
                i["id"],
                1 if c.needs_attention else 0,
                c.category,
                c.urgency,
                c.confidence,
                c.reason,
                c.recommended_action,
                now_iso()
            ))

            created += 1

            if c.needs_attention:
                existing = conn.execute(
                    "SELECT id FROM attention_items WHERE item_id = ?",
                    (i["id"],)
                ).fetchone()

                if not existing:
                    attn_id = f"attn_{uuid4().hex}"
                    conn.execute("""
                        INSERT INTO attention_items
                        (id, item_id, status, surfaced_at)
                        VALUES (?, ?, 'active', ?)
                    """, (attn_id, i["id"], now_iso()))
                    surfaced += 1

    return {
        "ok": True,
        "classified": created,
        "surfaced": surfaced,
        "phone": phone_payload()
    }

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    connections.add(ws)
    try:
        await ws.send_text(json.dumps({"type": "phone", "phone": phone_payload()}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        connections.discard(ws)
    except Exception:
        connections.discard(ws)
