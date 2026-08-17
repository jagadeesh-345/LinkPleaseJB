from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field, field_validator


class RuleCreate(BaseModel):
    keyword: str = Field(..., description="Keyword to match in comments")
    dm_message: str = Field(..., description="DM message to send when rule matches")

    @field_validator("keyword", "dm_message")

    def check_not_empty(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return v_stripped


class RuleResponse(BaseModel):
    rule_id: str
    keyword: str
    dm_message: str


class RuleInDB(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:10]}")
    keyword: str
    normalized_keyword: str
    dm_message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, keyword: str, dm_message: str) -> "RuleInDB":
        kw_trimmed = keyword.strip()
        msg_trimmed = dm_message.strip()
        return cls(
            rule_id=f"rule_{uuid.uuid4().hex[:10]}",
            keyword=kw_trimmed,
            normalized_keyword=kw_trimmed.upper(),
            dm_message=msg_trimmed,
            created_at=datetime.now(timezone.utc),
        )
