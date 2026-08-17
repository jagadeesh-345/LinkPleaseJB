from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.models.rule import RuleCreate, RuleResponse
from app.services.rule_service import RuleService

router = APIRouter(tags=["Rules"])


@router.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_in: RuleCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    service = RuleService(db)
    return await service.create_rule(
        keyword=rule_in.keyword,
        dm_message=rule_in.dm_message
    )
