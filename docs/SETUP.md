# Setup

## 1. Deploy backend

Deploy `backend/` to Render.

Set env vars:

```text
PUBLIC_BASE_URL=https://your-service.onrender.com
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
CLASSIFIER_PROVIDER=mock
DB_PATH=/tmp/attention_os.db
```

## 2. Google Cloud

Create OAuth Web Client.

Redirect URI:

```text
https://your-service.onrender.com/auth/google/callback
```

Scopes used:

```text
openid
email
profile
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/calendar.readonly
```

## 3. Connect Google

Open backend dashboard:

```text
https://your-service.onrender.com
```

Click:

```text
Connect Google
```

Then click:

```text
Sync Google Now
```

## 4. Phone

Open Android Studio:

```text
android/AttentionGuardOS
```

Edit:

```text
app/src/main/java/com/attentionguard/os/BackendClient.kt
```

Set `BACKEND_URL`.

Run `app` on phone.

Grant:
- notification permission
- notification access

## 5. Galaxy Watch

In Android Studio, choose run configuration/module:

```text
wear
```

Run on watch or Wear emulator.

Edit:

```text
wear/src/main/java/com/attentionguard/wear/WearBackendClient.kt
```

Set same `BACKEND_URL`.
