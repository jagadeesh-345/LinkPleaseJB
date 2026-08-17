from datetime import datetime, timezone
import httpx
import pytest
from app.models.dm_job import DMJob, JobStatus
from app.services.dm_service import DMService
from app.utils.rate_limiter import AsyncRateLimiter


@pytest.mark.asyncio
async def test_500_error_schedules_retry(test_db):
    rate_limiter = AsyncRateLimiter()

    # Create transport that returns 500
    handler = lambda req: httpx.Response(500, json={"error": "Internal Server Error"})
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)

    dm_service = DMService(test_db, rate_limiter, http_client=http_client)

    job = DMJob(
        job_id="job_500",
        rule_id="r_1",
        user_id="u_1",
        comment_id="c_1",
        message="Test 500",
        status=JobStatus.QUEUED,
        attempt_count=0
    )
    await test_db.dm_jobs.insert_one(job.model_dump())

    await dm_service.execute_dm_job(job.model_dump())

    updated = await test_db.dm_jobs.find_one({"job_id": "job_500"})
    assert updated["status"] == JobStatus.RETRYING.value
    assert updated["attempt_count"] == 1
    assert "500" in updated["last_error"]


@pytest.mark.asyncio
async def test_400_error_marks_failed(test_db):
    rate_limiter = AsyncRateLimiter()

    # Create transport that returns 400
    handler = lambda req: httpx.Response(400, json={"error": "Invalid request"})
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)

    dm_service = DMService(test_db, rate_limiter, http_client=http_client)

    job = DMJob(
        job_id="job_400",
        rule_id="r_1",
        user_id="u_2",
        comment_id="c_2",
        message="Test 400",
        status=JobStatus.QUEUED,
        attempt_count=0
    )
    await test_db.dm_jobs.insert_one(job.model_dump())

    await dm_service.execute_dm_job(job.model_dump())

    updated = await test_db.dm_jobs.find_one({"job_id": "job_400"})
    assert updated["status"] == JobStatus.FAILED.value
    assert updated["attempt_count"] == 1
    assert "400" in updated["last_error"]


@pytest.mark.asyncio
async def test_429_retry_after(test_db):
    rate_limiter = AsyncRateLimiter()

    handler = lambda req: httpx.Response(429, headers={"Retry-After": "3"}, json={"error": "Rate limit exceeded"})
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)

    dm_service = DMService(test_db, rate_limiter, http_client=http_client)

    job = DMJob(
        job_id="job_429",
        rule_id="r_1",
        user_id="u_3",
        comment_id="c_3",
        message="Test 429",
        status=JobStatus.QUEUED,
        attempt_count=0
    )
    await test_db.dm_jobs.insert_one(job.model_dump())

    await dm_service.execute_dm_job(job.model_dump())

    assert rate_limiter.cooldown_until > 0

    updated = await test_db.dm_jobs.find_one({"job_id": "job_429"})
    assert updated["status"] == JobStatus.RETRYING.value
    assert "429" in updated["last_error"]
