from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class FromUser(BaseModel):
    user_id: str
    username: str


class CommentData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    comment_id: str
    post_id: Optional[str] = None
    text: Optional[str] = None
    created_at: Optional[str] = None
    from_user: Optional[FromUser] = Field(None, alias="from")



class WebhookEventPayload(BaseModel):
    event_id: str
    event_type: str
    sent_at: str
    data: Optional[Dict[str, Any]] = None


class EventInDB(BaseModel):
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    status: str = "accepted"
