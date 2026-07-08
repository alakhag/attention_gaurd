# Attention Guard — Realtime Deployable Prototype

This is a deliberately simple, imperfect, deployable prototype.

It does this:

```text
Android notification / fake test notification
↓
POST /android/notifications
↓
classifier decides attention vs not attention
↓
SQLite stores item
↓
dashboard updates live via WebSocket
↓
status becomes:
  Nothing important missed
  or
  X things need attention
```

## Included

- FastAPI backend
- SQLite persistence
- WebSocket live dashboard
- Notification ingestion API
- Attention item dismiss/resolve
- Mock AI classifier
- Optional OpenAI classifier hook
- Dockerfile
- Render deploy config
- Android NotificationListenerService bridge skeleton

## Quick local run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Test

```bash
bash test_live.sh
```

## Deploy to Render

1. Push this repo to GitHub.
2. Render → New → Web Service.
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Default classifier is `mock`, so no API key is required.
