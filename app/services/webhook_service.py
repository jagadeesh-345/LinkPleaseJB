from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import pymongo.errors

from app.models.dm_job import DMJob, JobStatus
from app.models.event import EventInDB
from app.services.rule_service import RuleService

logger = logging.getLogger(__name__)


class WebhookService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.rule_service = RuleService(db)

    async def process_incoming_event(self, payload: Dict[str, Any]) -> Dict[str, str]:
        event_id = payload.get("event_id")
        event_type = payload.get("event_type")

        if not event_id or not event_type:
            raise ValueError("Missing required webhook fields: event_id or event_type")

        # 1. Webhook Idempotency Check via Database Unique Constraint
        event_doc = EventInDB(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            received_at=datetime.now(timezone.utc),
            status="accepted"
        ).model_dump()

        try:
            await self.db.events.insert_one(event_doc)
            logger.info(f"event_received: event_id={event_id}, type={event_type}")
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"event_duplicate: event_id={event_id} already exists. Ignoring gracefully.")
            return {"status": "accepted", "detail": "duplicate_event_ignored"}

        # 2. Dispatch handling based on event_type
        if event_type == "comment.created":
            await self._handle_comment_created(payload)
        elif event_type == "comment.deleted":
            await self._handle_comment_deleted(payload)

        return {"status": "accepted"}

    async def _handle_comment_created(self, payload: Dict[str, Any]):
        data = payload.get("data") or {}
        comment_id = data.get("comment_id")
        text = data.get("text", "")
        from_user = data.get("from") or {}
        user_id = from_user.get("user_id")

        if not comment_id or not user_id:
            logger.warning(f"Malformed comment.created event data: {data}")
            return

        # Match text against active rules
        matched_rules = await self.rule_service.match_text(text)
        if not matched_rules:
            logger.info(f"No rules matched for comment_id={comment_id}, text='{text}'")
            return

        for rule in matched_rules:
            logger.info(f"rule_matched: rule_id={rule.rule_id}, user_id={user_id}, comment_id={comment_id}")
            job = DMJob(
                rule_id=rule.rule_id,
                user_id=user_id,
                comment_id=comment_id,
                message=rule.dm_message,
                status=JobStatus.QUEUED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Atomic insert enforcing unique constraint on (rule_id, user_id)
            try:
                await self.db.dm_jobs.insert_one(job.model_dump())
                logger.info(f"dm_queued: job_id={job.job_id}, rule_id={rule.rule_id}, user_id={user_id}")
            except pymongo.errors.DuplicateKeyError:
                logger.info(
                    f"duplicate_dm_blocked: user_id={user_id} has already been processed for rule_id={rule.rule_id}"
                )
                await self.db.duplicate_blocks.insert_one({
                    "rule_id": rule.rule_id,
                    "user_id": user_id,
                    "comment_id": comment_id,
                    "event_id": payload.get("event_id"),
                    "blocked_at": datetime.now(timezone.utc)
                })

    async def _handle_comment_deleted(self, payload: Dict[str, Any]):
        data = payload.get("data") or {}
        comment_id = data.get("comment_id")
        if not comment_id:
            logger.warning(f"comment.deleted event missing comment_id in payload: {payload}")
            return

        result = await self.db.dm_jobs.update_many(
            {
                "comment_id": comment_id,
                "status": {"$in": [JobStatus.QUEUED.value, JobStatus.RETRYING.value, JobStatus.SENDING.value]}
            },
            {
                "$set": {
                    "status": JobStatus.CANCELLED.value,
                    "updated_at": datetime.now(timezone.utc),
                    "last_error": "Comment deleted by user prior to DM dispatch"
                }
            }
        )
        logger.info(f"comment_deleted: comment_id={comment_id}, cancelled_jobs={result.modified_count}")
