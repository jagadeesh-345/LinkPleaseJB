import pytest
from app.services.rule_service import RuleService


@pytest.mark.asyncio
async def test_create_rule(async_client, test_db):
    response = await async_client.post("/rules", json={
        "keyword": "  PRICE  ",
        "dm_message": "  Here is the price list!  "
    })
    assert response.status_code == 201
    data = response.json()
    assert "rule_id" in data
    assert data["keyword"] == "PRICE"
    assert data["dm_message"] == "Here is the price list!"


@pytest.mark.asyncio
async def test_rule_matching(test_db):
    service = RuleService(test_db)
    await service.create_rule(keyword="PRICE", dm_message="Price details")

    # Case-insensitive substring matches
    matches1 = await service.match_text("PRICE please 🙏")
    assert len(matches1) == 1

    matches2 = await service.match_text("what is the price?")
    assert len(matches2) == 1

    matches3 = await service.match_text("Send me Price list")
    assert len(matches3) == 1

    # Non-matching text
    matches4 = await service.match_text("Hello there!")
    assert len(matches4) == 0
