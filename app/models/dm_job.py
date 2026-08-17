from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    SENDING = "sending"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DMJob(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:12]}")
    rule_id: str
    user_id: str
    comment_id: str
    message: str
    status: JobStatus = JobStatus.QUEUED
    attempt_count: int = 0
    dm_id: Optional[str] = None
    next_attempt_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_error: Optional[str] = None
