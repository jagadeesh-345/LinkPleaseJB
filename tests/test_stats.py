from datetime import datetime, timezone
import pytest
from app.models.dm_job import DMJob, JobStatus


@pytest.mark.asyncio
async def test_stats_accuracy(async_client, test_db):
    # Insert delivered job (sent=1)
    j1 = DMJob(job_id="j1", rule_id="r1", user_id="u1", comment_id="c1", message="m", status=JobStatus.DELIVERED)
    # Insert accepted job (queued=1, sent=0)
    j2 = DMJob(job_id="j2", rule_id="r1", user_id="u2", comment_id="c2", message="m", status=JobStatus.ACCEPTED, dm_id="dm_j2")
    # Insert failed job (failed=1)
    j3 = DMJob(job_id="j3", rule_id="r1", user_id="u3", comment_id="c3", message="m", status=JobStatus.FAILED)
    # Insert queued job (queued=2 total)
    j4 = DMJob(job_id="j4", rule_id="r1", user_id="u4", comment_id="c4", message="m", status=JobStatus.QUEUED)

    await test_db.dm_jobs.insert_many([
        j1.model_dump(), j2.model_dump(), j3.model_dump(), j4.model_dump()
    ])

    # Insert a duplicate block record
    await test_db.duplicate_blocks.insert_one({
        "rule_id": "r1", "user_id": "u1", "comment_id": "c1_dup", "blocked_at": datetime.now(timezone.utc)
    })

    res = await async_client.get("/stats")
    assert res.status_code == 200
    data = res.json()

    assert data["sent"] == 1
    assert data["failed"] == 1
    assert data["queued"] == 2  # j2 (ACCEPTED) + j4 (QUEUED)
    assert data["duplicates_blocked"] == 1
