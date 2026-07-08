import os
import json
import httpx
from app.models import Classification

SYSTEM_PROMPT = """
You are the Attention Guard classifier.

The user's goal:
They want to stop checking their phone/email/calendar compulsively.
Only surface things that truly need attention.

Classify the item into:
- needs_attention: true/false
- category:
  urgent_email, today_calendar, urgent_notification, security_login_otp,
  bills_payment, work_immigration_legal, health_family_urgent,
  real_person_waiting, fyi, ignore
- urgency: now, today, later, none
- confidence: 0 to 1
- reason: short reason
- recommended_action: short action

Rules:

EMAIL:
Only surface unread emails if they are genuinely urgent/actionable:
- payment failure, bill/rent issue, account/security issue
- legal/immigration/work deadline
- human waiting for reply on something time-sensitive
- travel/health/family urgent issue
Ignore:
- promotions
- social
- newsletters
- receipts/order updates unless problem/failure
- job recommendations unless there is a concrete deadline/action
- generic FYI

CALENDAR:
Today's real events should usually surface because the user asked to be informed of today's important events.
Ignore all-day holidays, birthdays, spam calendars, declined events, and passive reminders.
For real meetings/events today, needs_attention=true, category=today_calendar.

NOTIFICATIONS:
Only surface urgent/actionable notifications:
- real person waiting now/today
- payment/security/health/family/calendar/work/legal/immigration
Ignore:
- system noise
- charging/USB/battery
- weather
- ChatGPT notifications
- social likes/comments/follows
- promotions
- passive FYI
"""

ALLOWED_CATEGORIES = {
    "urgent_email",
    "today_calendar",
    "urgent_notification",
    "security_login_otp",
    "bills_payment",
    "work_immigration_legal",
    "health_family_urgent",
    "real_person_waiting",
    "fyi",
    "ignore",
}
ALLOWED_URGENCY = {"now", "today", "later", "none"}

IGNORE_PACKAGES = {
    "android",
    "com.android.systemui",
    "com.openai.chatgpt",
    "com.google.android.googlequicksearchbox",
}

def classify_text(source: str, app_name: str | None, sender: str | None, title: str | None, body: str | None) -> Classification:
    # Hard package/source guardrails first. AI should not waste time on obvious noise.
    source_l = (source or "").lower()
    app_l = (app_name or "").lower()
    text_l = f"{source or ''} {app_name or ''} {sender or ''} {title or ''} {body or ''}".lower()

    if any(pkg in text_l for pkg in IGNORE_PACKAGES):
        return Classification(
            needs_attention=False,
            category="ignore",
            urgency="none",
            confidence=0.99,
            reason="Ignored system/app noise.",
            recommended_action="No action."
        )

    if any(x in text_l for x in ["usb for file transfer", "charging stopped", "battery", "weather", "sunny", "forecast"]):
        return Classification(
            needs_attention=False,
            category="ignore",
            urgency="none",
            confidence=0.99,
            reason="Ignored passive system/weather notification.",
            recommended_action="No action."
        )

    # Require real AI for actual semantic decisions.
    if os.getenv("OPENAI_API_KEY"):
        try:
            return classify_openai(source, app_name, sender, title, body)
        except Exception as e:
            return Classification(
                needs_attention=False,
                category="fyi",
                urgency="none",
                confidence=0.0,
                reason=f"AI classification failed: {type(e).__name__}",
                recommended_action="Check manually if needed."
            )

    # No mock fallback. If no AI key, fail closed.
    return Classification(
        needs_attention=False,
        category="fyi",
        urgency="none",
        confidence=0.0,
        reason="AI classifier not configured.",
        recommended_action="Set OPENAI_API_KEY and CLASSIFIER_PROVIDER=openai."
    )

def classify_openai(source, app_name, sender, title, body) -> Classification:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "source": source,
                "app_name": app_name,
                "sender": sender,
                "title": title,
                "body": body,
            })}
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "attention_classification",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "needs_attention",
                        "category",
                        "urgency",
                        "confidence",
                        "reason",
                        "recommended_action"
                    ],
                    "properties": {
                        "needs_attention": {"type": "boolean"},
                        "category": {
                            "type": "string",
                            "enum": sorted(ALLOWED_CATEGORIES)
                        },
                        "urgency": {
                            "type": "string",
                            "enum": sorted(ALLOWED_URGENCY)
                        },
                        "confidence": {"type": "number"},
                        "reason": {"type": "string"},
                        "recommended_action": {"type": "string"}
                    }
                },
                "strict": True
            }
        }
    }

    with httpx.Client(timeout=30) as client:
        r = client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        r.raise_for_status()
        data = r.json()

    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ["output_text", "text"]:
                    text = content.get("text")
                    break
            if text:
                break

    if not text:
        raise RuntimeError("No output_text from OpenAI")

    parsed = json.loads(text)

    # Defensive validation.
    if parsed.get("category") not in ALLOWED_CATEGORIES:
        parsed["category"] = "fyi"
        parsed["needs_attention"] = False
    if parsed.get("urgency") not in ALLOWED_URGENCY:
        parsed["urgency"] = "none"

    return Classification(**parsed)
