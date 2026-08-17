import logging
from typing import Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.dm_job import JobStatus

logger = logging.getLogger(__name__)


class StatsService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_statistics(self) -> Dict[str, int]:
        """
        Derives real-time system statistics from persistent database records.
        """
        # Sent: Confirmed delivered
        sent_count = await self.db.dm_jobs.count_documents({"status": JobStatus.DELIVERED.value})

        # Failed: Permanently failed
        failed_count = await self.db.dm_jobs.count_documents({"status": JobStatus.FAILED.value})

        # Queued: In-flight or waiting (queued, sending, accepted, retrying)
        queued_count = await self.db.dm_jobs.count_documents({
            "status": {
                "$in": [
                    JobStatus.QUEUED.value,
                    JobStatus.SENDING.value,
                    JobStatus.ACCEPTED.value,
                    JobStatus.RETRYING.value
                ]
            }
        })

        # Duplicates blocked: count from duplicate_blocks collection
        duplicates_blocked_count = await self.db.duplicate_blocks.count_documents({})

        return {
            "sent": sent_count,
            "failed": failed_count,
            "queued": queued_count,
            "duplicates_blocked": duplicates_blocked_count
        }
