import json
import pytest
from app.models.dm_job import DMJob, JobStatus
from tests.conftest import generate_test_signature


@pytest.mark.asyncio
async def test_webhook_fast_response_and_idempotency(async_client, test_db):
    payload = {
        "event_id": "evt_001",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22.481Z",
        "data": {
            "comment_id": "cmt_100",
            "post_id": "post_100",
            "text": "PRICE please",
            "created_at": "2026-08-10T09:14:21.900Z",
            "from": {
                "user_id": "usr_100",
                "username": "user100"
            }
        }
    }

    raw_body = json.dumps(payload).encode("utf-8")
    sig = generate_test_signature(raw_body)

    # First request
    response1 = await async_client.post(
        "/webhook",
        content=raw_body,
        headers={"X-PseudoGram-Signature": sig, "Content-Type": "application/json"}
    )
    assert response1.status_code == 200
    assert response1.json()["status"] == "accepted"

    # Second duplicate request with exact same event_id
    response2 = await async_client.post(
        "/webhook",
        content=raw_body,
        headers={"X-PseudoGram-Signature": sig, "Content-Type": "application/json"}
    )
    assert response2.status_code == 200
    assert response2.json()["status"] == "accepted"

    # DB verify event only inserted once
    events_count = await test_db.events.count_documents({"event_id": "evt_001"})
    assert events_count == 1


@pytest.mark.asyncio
async def test_comment_deleted_event(async_client, test_db):
    # Insert a queued job
    job = DMJob(
        rule_id="rule_1",
        user_id="usr_200",
        comment_id="cmt_200",
        message="Price info",
        status=JobStatus.QUEUED
    )
    await test_db.dm_jobs.insert_one(job.model_dump())

    payload = {
        "event_id": "evt_del_001",
        "event_type": "comment.deleted",
        "sent_at": "2026-08-10T09:15:22.481Z",
        "data": {
            "comment_id": "cmt_200"
        }
    }

    raw_body = json.dumps(payload).encode("utf-8")
    sig = generate_test_signature(raw_body)

    response = await async_client.post(
        "/webhook",
        content=raw_body,
        headers={"X-PseudoGram-Signature": sig, "Content-Type": "application/json"}
    )
    assert response.status_code == 200

    # Job status should now be CANCELLED
    updated_job = await test_db.dm_jobs.find_one({"comment_id": "cmt_200"})
    assert updated_job["status"] == JobStatus.CANCELLED.value
