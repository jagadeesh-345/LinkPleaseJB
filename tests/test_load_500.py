import asyncio
import json
import time
import httpx
from httpx import ASGITransport
from mongomock_motor import AsyncMongoMockClient
import pytest

from app.database.mongodb import db_manager
from app.main import app
from app.services.rule_service import RuleService
from tests.conftest import generate_test_signature


@pytest.mark.asyncio
async def test_500_events_load():
    client = AsyncMongoMockClient()
    db = client["test_linkplease_load_db"]

    db_manager.client = client
    db_manager.db = db
    await db_manager.init_indexes()

    await db.events.delete_many({})
    await db.dm_jobs.delete_many({})
    await db.rules.delete_many({})
    await db.duplicate_blocks.delete_many({})

    rule_service = RuleService(db)
    await rule_service.create_rule("PRICE", "Here is our pricing!")

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        print("\n--- STARTING 500 WEBHOOK EVENTS LOAD TEST ---")
        start_time = time.monotonic()

        tasks = []
        for i in range(500):
            # Duplicate event_ids repeat every 250
            event_id = f"evt_load_{i % 250}"
            # Users range 1 to 50
            user_id = f"user_{i % 50}"

            payload = {
                "event_id": event_id,
                "event_type": "comment.created",
                "sent_at": "2026-08-10T09:14:22.481Z",
                "data": {
                    "comment_id": f"cmt_load_{i}",
                    "text": "PRICE please 🙏" if i % 2 == 0 else "hello world",
                    "from": {
                        "user_id": user_id,
                        "username": f"user_{user_id}"
                    }
                }
            }
            raw_body = json.dumps(payload).encode("utf-8")
            sig = generate_test_signature(raw_body)

            tasks.append(
                async_client.post(
                    "/webhook",
                    content=raw_body,
                    headers={"X-PseudoGram-Signature": sig, "Content-Type": "application/json"}
                )
            )

        responses = await asyncio.gather(*tasks)
        end_time = time.monotonic()
        total_duration = end_time - start_time

        status_codes = [r.status_code for r in responses]
        successful_200s = status_codes.count(200)

        events_persisted = await db.events.count_documents({})
        jobs_created = await db.dm_jobs.count_documents({})
        duplicates_blocked = await db.duplicate_blocks.count_documents({})

        print(f"Total Requests Sent: {len(responses)}")
        print(f"Total Time Taken: {total_duration:.3f} seconds")
        print(f"Average Response Time: {(total_duration / len(responses)) * 1000:.2f} ms/req")
        print(f"Successful HTTP 200 Responses: {successful_200s}")
        print(f"Unique Events Persisted in DB: {events_persisted}")
        print(f"Unique DM Jobs Created: {jobs_created}")
        print(f"Duplicate DM Attempts Blocked: {duplicates_blocked}")
        print("---------------------------------------------\n")

        assert successful_200s == 500
        assert total_duration < 10.0
        assert events_persisted == 250
        assert jobs_created <= 50


if __name__ == "__main__":
    asyncio.run(test_500_events_load())
