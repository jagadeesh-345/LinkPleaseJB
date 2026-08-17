import json
import pytest
from app.services.rule_service import RuleService
from tests.conftest import generate_test_signature


@pytest.mark.asyncio
async def test_duplicate_user_same_rule_blocked(async_client, test_db):
    rule_service = RuleService(test_db)
    rule = await rule_service.create_rule("PRICE", "Price info")

    # Send 2 webhook comments from same user for same rule
    payload1 = {
        "event_id": "evt_101",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22Z",
        "data": {
            "comment_id": "cmt_101",
            "text": "PRICE please",
            "from": {"user_id": "usr_999", "username": "alice"}
        }
    }
    payload2 = {
        "event_id": "evt_102",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:15:22Z",
        "data": {
            "comment_id": "cmt_102",
            "text": "PRICE list?",
            "from": {"user_id": "usr_999", "username": "alice"}
        }
    }

    raw1 = json.dumps(payload1).encode("utf-8")
    raw2 = json.dumps(payload2).encode("utf-8")

    res1 = await async_client.post("/webhook", content=raw1, headers={"X-PseudoGram-Signature": generate_test_signature(raw1)})
    assert res1.status_code == 200

    res2 = await async_client.post("/webhook", content=raw2, headers={"X-PseudoGram-Signature": generate_test_signature(raw2)})
    assert res2.status_code == 200

    # Verify only 1 DM job queued for user usr_999 and rule
    job_count = await test_db.dm_jobs.count_documents({"rule_id": rule.rule_id, "user_id": "usr_999"})
    assert job_count == 1

    # Verify 1 duplicate block recorded
    blocked_count = await test_db.duplicate_blocks.count_documents({"rule_id": rule.rule_id, "user_id": "usr_999"})
    assert blocked_count == 1


@pytest.mark.asyncio
async def test_different_users_same_rule(async_client, test_db):
    rule_service = RuleService(test_db)
    rule = await rule_service.create_rule("DISCOUNT", "Here is your discount code")

    p1 = {
        "event_id": "evt_201",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22Z",
        "data": {"comment_id": "c1", "text": "DISCOUNT", "from": {"user_id": "user_A", "username": "a"}}
    }
    p2 = {
        "event_id": "evt_202",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:23Z",
        "data": {"comment_id": "c2", "text": "DISCOUNT", "from": {"user_id": "user_B", "username": "b"}}
    }

    raw1 = json.dumps(p1).encode("utf-8")
    raw2 = json.dumps(p2).encode("utf-8")

    await async_client.post("/webhook", content=raw1, headers={"X-PseudoGram-Signature": generate_test_signature(raw1)})
    await async_client.post("/webhook", content=raw2, headers={"X-PseudoGram-Signature": generate_test_signature(raw2)})

    job_count = await test_db.dm_jobs.count_documents({"rule_id": rule.rule_id})
    assert job_count == 2


@pytest.mark.asyncio
async def test_same_user_different_rules(async_client, test_db):
    rule_service = RuleService(test_db)
    r1 = await rule_service.create_rule("CATALOG", "Catalog info")
    r2 = await rule_service.create_rule("COUPON", "Coupon info")

    p1 = {
        "event_id": "evt_301",
        "event_type": "comment.created",
        "sent_at": "2026-08-10T09:14:22Z",
        "data": {"comment_id": "c3", "text": "CATALOG and COUPON", "from": {"user_id": "user_C", "username": "c"}}
    }

    raw1 = json.dumps(p1).encode("utf-8")
    await async_client.post("/webhook", content=raw1, headers={"X-PseudoGram-Signature": generate_test_signature(raw1)})

    jobs_r1 = await test_db.dm_jobs.count_documents({"rule_id": r1.rule_id, "user_id": "user_C"})
    jobs_r2 = await test_db.dm_jobs.count_documents({"rule_id": r2.rule_id, "user_id": "user_C"})

    assert jobs_r1 == 1
    assert jobs_r2 == 1
