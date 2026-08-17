import httpx
import pytest
from app.models.dm_job import DMJob, JobStatus
from app.services.dm_service import DMService
from app.utils.rate_limiter import AsyncRateLimiter


@pytest.mark.asyncio
async def test_reconciliation_transitions_to_delivered(test_db):
    rate_limiter = AsyncRateLimiter()

    # Remote status endpoint returns "delivered"
    handler = lambda req: httpx.Response(200, json={"dm_id": "dm_777", "status": "delivered"})
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)

    dm_service = DMService(test_db, rate_limiter, http_client=http_client)

    job = DMJob(
        job_id="job_recon_1",
        rule_id="r_1",
        user_id="u_77",
        comment_id="c_77",
        message="Recon test",
        status=JobStatus.ACCEPTED,
        dm_id="dm_777"
    )
    await test_db.dm_jobs.insert_one(job.model_dump())

    await dm_service.reconcile_dm_status(job.model_dump())

    updated = await test_db.dm_jobs.find_one({"job_id": "job_recon_1"})
    assert updated["status"] == JobStatus.DELIVERED.value
