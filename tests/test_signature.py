import json
import pytest
from tests.conftest import generate_test_signature


@pytest.mark.asyncio
async def test_invalid_signature_rejected(async_client, test_db):
    payload = {"event_id": "evt_sig_test", "event_type": "comment.created", "sent_at": "2026-08-10T09:00:00Z"}
    raw_body = json.dumps(payload).encode("utf-8")

    # Missing signature header
    res1 = await async_client.post("/webhook", content=raw_body)
    assert res1.status_code == 401

    # Invalid signature header
    res2 = await async_client.post(
        "/webhook",
        content=raw_body,
        headers={"X-PseudoGram-Signature": "sha256=invalid_hex_string"}
    )
    assert res2.status_code == 401

    # Valid signature header
    valid_sig = generate_test_signature(raw_body)
    res3 = await async_client.post(
        "/webhook",
        content=raw_body,
        headers={"X-PseudoGram-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert res3.status_code == 200
