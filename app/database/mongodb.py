import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        target_uri = uri or settings.MONGODB_URI
        target_db = db_name or settings.DATABASE_NAME
        logger.info(f"Connecting to MongoDB at {target_uri}, db={target_db}")
        self.client = AsyncIOMotorClient(target_uri)
        self.db = self.client[target_db]
        await self.init_indexes()

    async def init_indexes(self):
        if self.db is None:
            return
        # Unique index on event_id for webhook idempotency
        await self.db.events.create_index("event_id", unique=True)

        # Unique index on (rule_id, user_id) for duplicate DM prevention
        await self.db.dm_jobs.create_index(
            [("rule_id", 1), ("user_id", 1)],
            unique=True,
            name="uniq_rule_user"
        )

        # Indexes for background worker polling and reconciliation
        await self.db.dm_jobs.create_index([("status", 1), ("next_attempt_at", 1)])
        await self.db.dm_jobs.create_index("comment_id")
        await self.db.dm_jobs.create_index("dm_id")
        await self.db.dm_jobs.create_index("job_id", unique=True)

        # Index on rules
        await self.db.rules.create_index("rule_id", unique=True)
        logger.info("MongoDB indexes verified/created successfully.")

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB client connection closed.")


db_manager = DatabaseManager()


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db
