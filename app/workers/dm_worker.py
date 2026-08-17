import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.dm_job import JobStatus
from app.services.dm_service import DMService
from app.utils.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


class DMWorker:

    def __init__(self, db: AsyncIOMotorDatabase, rate_limiter: Optional[AsyncRateLimiter] = None, http_client: Optional[httpx.AsyncClient] = None):
        self.db = db
        self.rate_limiter = rate_limiter or AsyncRateLimiter(
            max_requests=settings.RATE_LIMIT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
        )
        self.dm_service = DMService(db, self.rate_limiter, http_client=http_client)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("DM Background Worker started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("DM Background Worker stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.process_pending_jobs()
                await self.process_reconciliation_jobs()
            except Exception as exc:
                logger.error(f"Error in worker main loop: {exc}", exc_info=True)
            await asyncio.sleep(settings.WORKER_POLL_INTERVAL)

    async def process_pending_jobs(self):
        """
        Fetches jobs ready for sending or retrying.
        """
        now = datetime.now(timezone.utc)
        cursor = self.db.dm_jobs.find({
            "status": {"$in": [JobStatus.QUEUED.value, JobStatus.RETRYING.value]},
            "next_attempt_at": {"$lte": now}
        }).limit(20)

        jobs = await cursor.to_list(length=20)
        for job in jobs:
            if not self._running:
                break
            await self.dm_service.execute_dm_job(job)

    async def process_reconciliation_jobs(self):
        """
        Fetches accepted jobs awaiting remote delivery verification.
        """
        cursor = self.db.dm_jobs.find({
            "status": JobStatus.ACCEPTED.value,
            "dm_id": {"$ne": None}
        }).limit(20)

        jobs = await cursor.to_list(length=20)
        for job in jobs:
            if not self._running:
                break
            await self.dm_service.reconcile_dm_status(job)
