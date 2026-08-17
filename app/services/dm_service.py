from datetime import datetime, timezone
import logging
from typing import Optional, Tuple
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.dm_job import DMJob, JobStatus
from app.services.retry_service import calculate_next_attempt
from app.utils.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


class DMService:

    def __init__(self, db: AsyncIOMotorDatabase, rate_limiter: AsyncRateLimiter, http_client: Optional[httpx.AsyncClient] = None):
        self.db = db
        self.rate_limiter = rate_limiter
        self.http_client = http_client or httpx.AsyncClient(timeout=10.0)

    async def execute_dm_job(self, job_dict: dict):
        job = DMJob(**job_dict)
        job_id = job.job_id
        attempt = job.attempt_count + 1

        logger.info(f"dm_send_attempt: job_id={job_id}, attempt={attempt}, user_id={job.user_id}")

        # Update status to SENDING
        await self.db.dm_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": JobStatus.SENDING.value, "updated_at": datetime.now(timezone.utc)}}
        )

        url = f"{settings.PSEUDOGRAM_BASE_URL.rstrip('/')}/v1/dm/send"
        headers = {
            "X-API-Key": settings.PSEUDOGRAM_API_KEY,
            "Idempotency-Key": f"{job.rule_id}:{job.user_id}",
            "Content-Type": "application/json"
        }
        payload = {
            "recipient_user_id": job.user_id,
            "message": job.message,
            "comment_id": job.comment_id
        }

        # Rate Limit Guard
        await self.rate_limiter.acquire()

        try:
            response = await self.http_client.post(url, json=payload, headers=headers)
            status_code = response.status_code

            if status_code == 202:
                resp_json = response.json()
                dm_id = resp_json.get("dm_id") or resp_json.get("id") or f"dm_{job_id}"
                logger.info(f"dm_send_success: job_id={job_id}, dm_id={dm_id}, status=202_accepted")

                await self.db.dm_jobs.update_one(
                    {"job_id": job_id},
                    {
                        "$set": {
                            "status": JobStatus.ACCEPTED.value,
                            "dm_id": dm_id,
                            "attempt_count": attempt,
                            "updated_at": datetime.now(timezone.utc),
                            "last_error": None
                        }
                    }
                )

            elif status_code == 429:
                retry_after_str = response.headers.get("Retry-After", "5")
                try:
                    retry_after = float(retry_after_str)
                except ValueError:
                    retry_after = 5.0

                logger.warning(f"dm_send_retry (429 Rate Limit): job_id={job_id}, retry_after={retry_after}s")
                await self.rate_limiter.set_cooldown(retry_after)

                next_attempt = datetime.now(timezone.utc) + httpx.math.timedelta(seconds=retry_after) if hasattr(httpx, "math") else calculate_next_attempt(attempt)
                await self._schedule_retry(job_id, attempt, next_attempt, f"429 Rate Limited (Retry-After: {retry_after}s)")

            elif status_code == 400:
                error_msg = f"HTTP 400 Bad Request: {response.text}"
                logger.error(f"dm_send_failed (Non-retryable 400): job_id={job_id}, error={error_msg}")
                await self._mark_failed(job_id, attempt, error_msg)

            elif status_code >= 500:
                error_msg = f"HTTP {status_code} Temporary Server Error: {response.text}"
                logger.warning(f"dm_send_retry (500 Server Error): job_id={job_id}, attempt={attempt}")
                next_attempt = calculate_next_attempt(attempt)
                await self._schedule_retry(job_id, attempt, next_attempt, error_msg)

            else:
                error_msg = f"Unexpected status code {status_code}: {response.text}"
                logger.warning(f"dm_send_retry: job_id={job_id}, error={error_msg}")
                next_attempt = calculate_next_attempt(attempt)
                await self._schedule_retry(job_id, attempt, next_attempt, error_msg)

        except (httpx.RequestError, Exception) as exc:
            error_msg = f"Network or execution exception: {str(exc)}"
            logger.warning(f"dm_send_retry (Exception): job_id={job_id}, error={error_msg}")
            next_attempt = calculate_next_attempt(attempt)
            await self._schedule_retry(job_id, attempt, next_attempt, error_msg)

    async def reconcile_dm_status(self, job_dict: dict):
        job = DMJob(**job_dict)
        job_id = job.job_id
        dm_id = job.dm_id

        if not dm_id:
            logger.warning(f"Reconciliation skipped for job_id={job_id}: missing dm_id")
            return

        url = f"{settings.PSEUDOGRAM_BASE_URL.rstrip('/')}/v1/dm/{dm_id}"
        headers = {"X-API-Key": settings.PSEUDOGRAM_API_KEY}

        await self.rate_limiter.acquire()

        try:
            response = await self.http_client.get(url, headers=headers)
            if response.status_code == 200:
                resp_json = response.json()
                remote_status = resp_json.get("status")
                logger.info(f"dm_delivery_checked: job_id={job_id}, dm_id={dm_id}, remote_status={remote_status}")

                if remote_status == "delivered":
                    logger.info(f"dm_delivered: job_id={job_id}, dm_id={dm_id}")
                    await self.db.dm_jobs.update_one(
                        {"job_id": job_id},
                        {
                            "$set": {
                                "status": JobStatus.DELIVERED.value,
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                elif remote_status == "failed":
                    logger.warning(f"dm_delivery_failed: job_id={job_id}, dm_id={dm_id}")
                    # Re-queue for retry if max retries not exceeded
                    next_attempt = calculate_next_attempt(job.attempt_count)
                    await self._schedule_retry(
                        job_id,
                        job.attempt_count,
                        next_attempt,
                        "Remote DM delivery reported failed during reconciliation"
                    )
                # If remote_status == "queued", stay in ACCEPTED status to check again on next cycle

        except Exception as exc:
            logger.warning(f"Reconciliation query error for dm_id={dm_id}: {exc}")

    async def _schedule_retry(self, job_id: str, attempt: int, next_attempt: datetime, error_msg: str):
        if attempt >= settings.MAX_RETRIES:
            logger.error(f"dm_send_failed: job_id={job_id} exceeded max retries ({settings.MAX_RETRIES})")
            await self._mark_failed(job_id, attempt, f"Exceeded max retries. Last error: {error_msg}")
        else:
            await self.db.dm_jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": JobStatus.RETRYING.value,
                        "attempt_count": attempt,
                        "next_attempt_at": next_attempt,
                        "updated_at": datetime.now(timezone.utc),
                        "last_error": error_msg
                    }
                }
            )

    async def _mark_failed(self, job_id: str, attempt: int, error_msg: str):
        await self.db.dm_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": JobStatus.FAILED.value,
                    "attempt_count": attempt,
                    "updated_at": datetime.now(timezone.utc),
                    "last_error": error_msg
                }
            }
        )
