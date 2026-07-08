# Attention OS V1

This is the first integrated version:

```text
Gmail API
Google Calendar API
Android Notification Listener
        ↓
Attention Engine backend
        ↓
Phone notification
Galaxy Watch app
Web dashboard
```

## What works

Backend:
- Google OAuth connect endpoint
- Gmail read sync
- Calendar read sync
- Android notification ingestion
- unified `/phone` endpoint
- attention item Done/Later endpoints
- SQLite persistence
- web dashboard

Phone app:
- listens to notifications
- sends notifications to backend
- shows Attention Guard summary notification
- shows per-item Done/Later notifications

Wear OS app:
- fetches `/phone`
- shows Clear / X things need attention
- Done / Later on first active item
- manual refresh

## What is still rough

- No production auth
- No encrypted token storage
- No Google verification flow/publishing
- No background scheduler
- No FCM push
- Wear app is an app, not a Tile yet
- Mock classifier unless you set OpenAI env vars

## Backend deploy

Render settings:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Environment variables:

```text
PUBLIC_BASE_URL=https://your-render-url.onrender.com
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
CLASSIFIER_PROVIDER=mock
DB_PATH=/tmp/attention_os.db
```

Google redirect URI:

```text
https://your-render-url.onrender.com/auth/google/callback
```

## Android

Open:

```text
android/AttentionGuardOS
```

in Android Studio.

Edit backend URLs in:

```text
app/src/main/java/com/attentionguard/os/BackendClient.kt
wear/src/main/java/com/attentionguard/wear/WearBackendClient.kt
```

Set both to your Render URL.

Run `app` on phone. Run `wear` on Galaxy Watch.
