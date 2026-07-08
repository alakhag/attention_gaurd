from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.db import init_db
from app.models import AndroidNotificationIn, StatusOut
from app.services.logic import (
    ingest_notification,
    get_status,
    list_attention_items,
    update_attention_status,
    list_items,
)
from app.services.realtime import hub

app = FastAPI(title="Attention Guard Realtime", version="0.3.0-deployable")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def dashboard():
    return FileResponse(static_dir / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "version": "0.3.0-deployable"}


@app.get("/status", response_model=StatusOut)
def status():
    return get_status()


@app.get("/attention-items")
def attention_items():
    return {"items": list_attention_items()}


@app.post("/attention-items/{attention_id}/dismiss")
async def dismiss(attention_id: str):
    ok = update_attention_status(attention_id, "dismissed")
    if not ok:
        raise HTTPException(status_code=404, detail="attention item not found")
    s = get_status()
    await hub.broadcast({"type": "status", "status": s})
    return {"ok": True, "status": s}


@app.post("/attention-items/{attention_id}/resolve")
async def resolve(attention_id: str):
    ok = update_attention_status(attention_id, "resolved")
    if not ok:
        raise HTTPException(status_code=404, detail="attention item not found")
    s = get_status()
    await hub.broadcast({"type": "status", "status": s})
    return {"ok": True, "status": s}


@app.post("/android/notifications")
async def android_notification(payload: AndroidNotificationIn):
    decision = ingest_notification(payload)
    s = get_status()
    await hub.broadcast({"type": "update", "status": s, "decision": decision})
    return {"accepted": True, "decision": decision, "status": s}


@app.get("/debug/items")
def debug_items():
    return {"items": list_items()}


@app.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        await websocket.send_json({"type": "status", "status": get_status()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)
    except Exception:
        hub.disconnect(websocket)
