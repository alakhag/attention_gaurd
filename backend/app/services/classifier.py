import os
import json
import httpx
from app.models import AndroidNotificationIn, Classification

SYSTEM_PROMPT = """
You are Attention Guard's classifier.

Classify whether a notification needs attention.

Return JSON only with:
needs_attention: boolean
category: one of scheduling, bills_payment, real_person_waiting, work_immigration_legal, security_login_otp, health_family_urgent, fyi, ignore
urgency: one of now, today, this_week, later, none
confidence: number 0..1
reason: short string
recommended_action: short string

Surface only if user likely needs to act, reply, decide, attend, pay, verify, or handle risk.
Ignore passive social likes, promotions, recommendations, generic updates, and non-actionable noise.
"""


def classify_notification(n: AndroidNotificationIn) -> Classification:
    provider = os.getenv("CLASSIFIER_PROVIDER", "mock").lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            return classify_with_openai(n)
        except Exception as e:
            return mock_classify(n, fallback_error=str(e))
    return mock_classify(n)


def mock_classify(n: AndroidNotificationIn, fallback_error: str | None = None) -> Classification:
    text = f"{n.app_name or ''} {n.title or ''} {n.body or ''}".lower()

    if any(x in text for x in ["liked your", "commented", "started following", "recommended", "sale", "coupon", "deal"]):
        return Classification(
            needs_attention=False,
            category="ignore",
            urgency="none",
            confidence=0.95,
            reason="Passive social/promotional notification.",
            recommended_action="No action.",
        )

    if any(x in text for x in ["payment", "rent", "declined", "overdue", "did not go through", "didn't go through", "account locked", "suspicious transaction"]):
        return Classification(
            needs_attention=True,
            category="bills_payment",
            urgency="today",
            confidence=0.88,
            reason="Looks like a payment, rent, bank, or account issue.",
            recommended_action="Open and verify.",
        )

    if any(x in text for x in ["available", "around later", "meet", "reschedule", "moved", "cancelled", "canceled", "calendar", "free later"]):
        return Classification(
            needs_attention=True,
            category="scheduling",
            urgency="today",
            confidence=0.84,
            reason="Looks like scheduling or availability.",
            recommended_action="Review and reply if needed.",
        )

    if any(x in text for x in ["uscis", "attorney", "lawyer", "immigration", "h1b", "h-1b", "o1", "o-1", "opt", "payroll", "offer letter"]):
        return Classification(
            needs_attention=True,
            category="work_immigration_legal",
            urgency="today",
            confidence=0.9,
            reason="Looks like work, legal, immigration, or payroll.",
            recommended_action="Review soon.",
        )

    if any(x in text for x in ["otp", "verification code", "password reset", "login", "sign-in", "suspicious"]):
        return Classification(
            needs_attention=True,
            category="security_login_otp",
            urgency="now",
            confidence=0.82,
            reason="Looks like login/security/OTP.",
            recommended_action="Verify if expected.",
        )

    if any(x in text for x in ["urgent", "doctor", "hospital", "bp", "blood pressure", "emergency", "flight issue", "call immediately"]):
        return Classification(
            needs_attention=True,
            category="health_family_urgent",
            urgency="now",
            confidence=0.9,
            reason="Looks urgent or health/family/travel related.",
            recommended_action="Check now.",
        )

    if any(x in text for x in ["?", "can you", "could you", "please", "call me", "reply", "confirm", "let me know", "when free"]):
        return Classification(
            needs_attention=True,
            category="real_person_waiting",
            urgency="today",
            confidence=0.78,
            reason="Looks like someone is asking for response/action.",
            recommended_action="Reply when available.",
        )

    reason = "No clear action needed."
    if fallback_error:
        reason += f" LLM fallback used: {fallback_error[:120]}"
    return Classification(
        needs_attention=False,
        category="fyi",
        urgency="none",
        confidence=0.6,
        reason=reason,
        recommended_action="No immediate action.",
    )


def classify_with_openai(n: AndroidNotificationIn) -> Classification:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "app_name": n.app_name,
                "package_name": n.package_name,
                "title": n.title,
                "body": n.body,
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
                        "category": {
                            "type": "string",
                            "enum": [
                                "scheduling", "bills_payment", "real_person_waiting",
                                "work_immigration_legal", "security_login_otp",
                                "health_family_urgent", "fyi", "ignore"
                            ]
                        },
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
        r = client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
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

    parsed = json.loads(text)
    return Classification(**parsed)
