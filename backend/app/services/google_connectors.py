import os
import time
import httpx
from urllib.parse import urlencode
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from email.utils import parseaddr
from zoneinfo import ZoneInfo

from app.db import db, now_iso
from app.services.attention import insert_and_classify, insert_forced_attention

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

def public_base_url():
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

def redirect_uri():
    return os.getenv("GOOGLE_REDIRECT_URI") or f"{public_base_url()}/auth/google/callback"

def auth_url():
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent select_account",
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH}?{urlencode(params)}"

def exchange_code(code: str):
    with httpx.Client(timeout=30) as client:
        r = client.post(GOOGLE_TOKEN, data={
            "code": code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        })
        r.raise_for_status()
        token = r.json()

        u = client.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {token['access_token']}"})
        u.raise_for_status()
        info = u.json()

    email = info["email"]
    expires_at = int(time.time()) + int(token.get("expires_in", 3600)) - 60
    refresh = token.get("refresh_token")

    with db() as conn:
        existing = conn.execute("SELECT refresh_token FROM google_accounts WHERE email = ?", (email,)).fetchone()
        if existing and not refresh:
            refresh = existing["refresh_token"]

        conn.execute("""
            INSERT INTO google_accounts (id, email, access_token, refresh_token, expires_at, scopes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                access_token=excluded.access_token,
                refresh_token=excluded.refresh_token,
                expires_at=excluded.expires_at,
                scopes=excluded.scopes,
                updated_at=excluded.updated_at
        """, (f"gacct_{uuid4().hex}", email, token["access_token"], refresh, expires_at,
              " ".join(SCOPES), now_iso(), now_iso()))
    return email

def connected_accounts():
    with db() as conn:
        rows = conn.execute("SELECT email, updated_at FROM google_accounts ORDER BY email").fetchall()
    return [dict(r) for r in rows]

def get_access_token(email):
    with db() as conn:
        row = conn.execute("SELECT * FROM google_accounts WHERE email = ?", (email,)).fetchone()
    if not row:
        raise RuntimeError("account not found")
    if row["expires_at"] and int(row["expires_at"]) > int(time.time()) + 30:
        return row["access_token"]

    with httpx.Client(timeout=30) as client:
        r = client.post(GOOGLE_TOKEN, data={
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": row["refresh_token"],
            "grant_type": "refresh_token",
        })
        r.raise_for_status()
        token = r.json()
    access = token["access_token"]
    expires = int(time.time()) + int(token.get("expires_in", 3600)) - 60
    with db() as conn:
        conn.execute("UPDATE google_accounts SET access_token=?, expires_at=?, updated_at=? WHERE email=?",
                     (access, expires, now_iso(), email))
    return access

def sync_all_google():
    results = []
    for acct in connected_accounts():
        email = acct["email"]
        results.append({
            "email": email,
            "gmail_unread": sync_gmail_unread(email),
            "calendar_today": sync_calendar_today(email)
        })
    return results

def sync_gmail_unread(email):
    token = get_access_token(email)

    # User intent:
    # - unread emails only
    # - exclude promotions/social/forums/categories
    # - AI decides whether urgent enough to surface
    q = "is:unread newer_than:7d -category:promotions -category:social -category:forums"

    inserted = 0
    seen = 0

    with httpx.Client(timeout=30) as client:
        r = client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": q, "maxResults": 50}
        )
        r.raise_for_status()
        messages = r.json().get("messages", [])

        for m in messages:
            seen += 1
            mid = m["id"]
            gr = client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "format": "metadata",
                    "metadataHeaders": ["From", "Subject", "Date", "List-Unsubscribe", "Precedence"]
                }
            )
            gr.raise_for_status()
            msg = gr.json()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

            # Skip common mailing-list/bulk mail before AI.
            if headers.get("list-unsubscribe") or headers.get("precedence", "").lower() in ["bulk", "list", "junk"]:
                continue

            from_raw = headers.get("from", "")
            sender_name, sender_email = parseaddr(from_raw)
            subject = headers.get("subject", "(no subject)")
            snippet = msg.get("snippet", "")

            res = insert_and_classify(
                source="gmail_unread",
                source_item_id=f"gmail:{email}:{mid}",
                account_email=email,
                app_name="Gmail",
                sender=sender_name or sender_email or from_raw,
                title=subject,
                body=snippet,
                timestamp=now_iso(),
            )
            if not res.get("deduped"):
                inserted += 1

    return {"seen_unread": seen, "inserted": inserted}

def sync_calendar_today(email):
    token = get_access_token(email)

    tz = ZoneInfo(os.getenv("USER_TIMEZONE", "America/Chicago"))
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)

    time_min = start_local.astimezone(timezone.utc).isoformat()
    time_max = end_local.astimezone(timezone.utc).isoformat()

    inserted = 0
    seen = 0

    with httpx.Client(timeout=30) as client:
        r = client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {token}"}
        )
        r.raise_for_status()
        calendars = r.json().get("items", [])

        for cal in calendars[:20]:
            cal_id = cal["id"]
            er = client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 50,
                }
            )
            if er.status_code >= 400:
                continue

            events = er.json().get("items", [])
            for ev in events:
                seen += 1

                if ev.get("status") == "cancelled":
                    continue

                attendees = ev.get("attendees", [])
                self_declined = any(
                    a.get("self") and a.get("responseStatus") == "declined"
                    for a in attendees
                )
                if self_declined:
                    continue

                title = ev.get("summary", "(calendar event)")
                title_l = title.lower()

                # Ignore passive calendar noise.
                if any(x in title_l for x in ["birthday", "holiday", "observance"]):
                    continue

                eid = ev.get("id")
                start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date") or ""
                end = ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date") or ""
                location = ev.get("location", "")
                organizer = ev.get("organizer", {}).get("email", "")
                desc = ev.get("description", "")
                body = f"Start: {start}\nEnd: {end}\nLocation: {location}\n{desc}".strip()

                res = insert_forced_attention(
                    source="calendar_today",
                    source_item_id=f"calendar:{email}:{cal_id}:{eid}",
                    account_email=email,
                    app_name="Google Calendar",
                    sender=organizer,
                    title=title,
                    body=body,
                    timestamp=start or now_iso(),
                    category="today_calendar",
                    urgency="today",
                    reason="Today's calendar event.",
                    recommended_action="Be aware / prepare if needed."
                )
                if not res.get("deduped"):
                    inserted += 1

    return {"seen_today": seen, "inserted": inserted}
