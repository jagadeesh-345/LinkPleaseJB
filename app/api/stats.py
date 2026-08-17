from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.services.stats_service import StatsService

router = APIRouter(tags=["Stats"])


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_stats(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    service = StatsService(db)
    return await service.get_statistics()
