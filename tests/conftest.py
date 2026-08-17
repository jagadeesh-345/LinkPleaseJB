import asyncio
import hashlib
import hmac
from typing import AsyncGenerator
import httpx
from httpx import ASGITransport
from mongomock_motor import AsyncMongoMockClient
import pytest

from app.config import settings
from app.database.mongodb import db_manager
from app.main import app
from tests.mock_pseudogram import MockPseudogramAPI


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    client = AsyncMongoMockClient()
    db = client["test_linkplease_db"]

    db_manager.client = client
    db_manager.db = db
    await db_manager.init_indexes()

    # Clean test collections before test
    await db.events.delete_many({})
    await db.dm_jobs.delete_many({})
    await db.rules.delete_many({})
    await db.duplicate_blocks.delete_many({})

    yield db

    # Cleanup after test
    await db.events.delete_many({})
    await db.dm_jobs.delete_many({})
    await db.rules.delete_many({})
    await db.duplicate_blocks.delete_many({})


@pytest.fixture
def mock_pseudogram():
    return MockPseudogramAPI()


@pytest.fixture
async def async_client(test_db, mock_pseudogram) -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def generate_test_signature(raw_body: bytes, secret_key: str = settings.PSEUDOGRAM_API_KEY) -> str:
    sig = hmac.new(secret_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"
