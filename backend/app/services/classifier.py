import os
import json
import httpx
from app.models import Classification

SYSTEM_PROMPT = """
You classify whether an item needs user attention.

Return JSON only with:
needs_attention, category, urgency, confidence, reason, recommended_action.

Categories:
scheduling, bills_payment, real_person_waiting, work_immigration_legal,
security_login_otp, health_family_urgent, fyi, ignore.

Surface only if the user likely needs to act, reply, decide, attend, pay, verify, or handle risk.
"""

def classify_text(source: str, app_name: str | None, sender: str | None, title: str | None, body: str | None) -> Classification:
    provider = os.getenv("CLASSIFIER_PROVIDER", "mock").lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            return classify_openai(source, app_name, sender, title, body)
        except Exception:
            return classify_mock(source, app_name, sender, title, body)
    return classify_mock(source, app_name, sender, title, body)

def classify_mock(source, app_name, sender, title, body) -> Classification:
    text = f"{source or ''} {app_name or ''} {sender or ''} {title or ''} {body or ''}".lower()

    if any(x in text for x in ["liked your", "commented", "started following", "recommended", "sale", "coupon", "deal"]):
        return Classification(False, "ignore", "none", 0.95, "Passive social/promotional noise.", "No action.")

    if any(x in text for x in ["payment", "rent", "declined", "overdue", "did not go through", "didn't go through", "account locked", "suspicious transaction", "bill due", "past due"]):
        return Classification(True, "bills_payment", "today", 0.9, "Payment, bill, rent, bank, or account issue.", "Open and verify.")

    if any(x in text for x in ["available", "around later", "meet", "reschedule", "moved", "cancelled", "canceled", "calendar", "free later", "invitation", "accepted:", "declined:"]):
        return Classification(True, "scheduling", "today", 0.86, "Scheduling, calendar, or availability item.", "Review schedule.")

    if any(x in text for x in ["uscis", "attorney", "lawyer", "immigration", "h1b", "h-1b", "o1", "o-1", "opt", "payroll", "offer letter", "hr"]):
        return Classification(True, "work_immigration_legal", "today", 0.9, "Work, legal, immigration, HR, or payroll item.", "Review soon.")

    if any(x in text for x in ["otp", "verification code", "password reset", "login", "sign-in", "suspicious"]):
        return Classification(True, "security_login_otp", "now", 0.82, "Login/security/OTP item.", "Verify if expected.")

    if any(x in text for x in ["urgent", "doctor", "hospital", "bp", "blood pressure", "emergency", "flight issue", "call immediately"]):
        return Classification(True, "health_family_urgent", "now", 0.9, "Urgent health/family/travel signal.", "Check now.")

    if any(x in text for x in ["?", "can you", "could you", "please", "call me", "reply", "confirm", "let me know", "when free"]):
        return Classification(True, "real_person_waiting", "today", 0.78, "Someone may be asking for response/action.", "Reply when available.")

    return Classification(False, "fyi", "none", 0.6, "No clear action needed.", "No immediate action.")

def classify_openai(source, app_name, sender, title, body) -> Classification:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "source": source, "app_name": app_name, "sender": sender,
                "title": title, "body": body
            })}
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "attention_classification",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["needs_attention", "category", "urgency", "confidence", "reason", "recommended_action"],
                    "properties": {
                        "needs_attention": {"type": "boolean"},
                        "category": {"type": "string", "enum": [
                            "scheduling", "bills_payment", "real_person_waiting", "work_immigration_legal",
                            "security_login_otp", "health_family_urgent", "fyi", "ignore"
                        ]},
                        "urgency": {"type": "string", "enum": ["now", "today", "this_week", "later", "none"]},
                        "confidence": {"type": "number"},
                        "reason": {"type": "string"},
                        "recommended_action": {"type": "string"}
                    }
                },
                "strict": True
            }
        }
    }
    with httpx.Client(timeout=20) as client:
        r = client.post("https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload)
        r.raise_for_status()
        data = r.json()
    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ["output_text", "text"]:
                    text = content.get("text")
                    break
            if text: break
    return Classification(**json.loads(text))
