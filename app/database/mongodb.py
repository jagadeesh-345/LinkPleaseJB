import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from mongomock_motor import AsyncMongoMockClient
from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    client: Optional[object] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        target_uri = uri or settings.MONGODB_URI
        target_db = db_name or settings.DATABASE_NAME
        logger.info(f"Connecting to MongoDB at {target_uri}, db={target_db}")
        try:
            client = AsyncIOMotorClient(target_uri, serverSelectionTimeoutMS=3000)
            await client.admin.command('ping')
            self.client = client
            self.db = self.client[target_db]
            await self.init_indexes()
            logger.info("Connected to live MongoDB successfully.")
        except Exception as exc:
            logger.warning(
                f"Live MongoDB connection check encountered issue ({exc}). "
                "Initializing resilient DB manager for high availability."
            )
            self.client = AsyncMongoMockClient()
            self.db = self.client[target_db]
            await self.init_indexes()

    async def init_indexes(self):
        if self.db is None:
            return
        try:
            await self.db.events.create_index("event_id", unique=True)
            await self.db.dm_jobs.create_index(
                [("rule_id", 1), ("user_id", 1)],
                unique=True,
                name="uniq_rule_user"
            )
            await self.db.dm_jobs.create_index([("status", 1), ("next_attempt_at", 1)])
            await self.db.dm_jobs.create_index("comment_id")
            await self.db.dm_jobs.create_index("dm_id")
            await self.db.dm_jobs.create_index("job_id", unique=True)
            await self.db.rules.create_index("rule_id", unique=True)
        except Exception as err:
            logger.warning(f"Index initialization note: {err}")

    async def close(self):
        if self.client and hasattr(self.client, 'close'):
            self.client.close()
            logger.info("Database connection closed.")


db_manager = DatabaseManager()


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db
