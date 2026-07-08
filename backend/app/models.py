from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AndroidNotificationIn(BaseModel):
    device_id: str = "android-phone"
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
