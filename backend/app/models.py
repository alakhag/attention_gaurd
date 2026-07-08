from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AndroidNotificationIn(BaseModel):
    device_id: str = "dev1"
    package_name: str
    app_name: str
    title: Optional[str] = None
    body: Optional[str] = None
    notification_key: str
    timestamp: Optional[datetime] = None


class Classification(BaseModel):
    needs_attention: bool
    category: str
    urgency: str
    confidence: float = Field(ge=0, le=1)
    reason: str
    recommended_action: str


class StatusOut(BaseModel):
    status: str
    attention_count: int
    summary: str
    top_items: list[str] = []
    last_checked_at: Optional[str] = None
