from contextlib import asynccontextmanager
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import rules, stats, webhook
from app.database.mongodb import db_manager
from app.workers.dm_worker import DMWorker

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("linkplease")

worker_instance = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_instance
    logger.info("Initializing LinkPlease Backend Application...")

    try:
        await db_manager.connect()
    except Exception as exc:
        logger.error(f"Error during db_manager connect: {exc}")

    try:
        if db_manager.db is not None:
            worker_instance = DMWorker(db_manager.db)
            await worker_instance.start()
    except Exception as exc:
        logger.error(f"Error starting background DM worker: {exc}")

    yield

    logger.info("Shutting down LinkPlease Backend Application...")
    try:
        if worker_instance:
            await worker_instance.stop()
    except Exception:
        pass
    try:
        await db_manager.close()
    except Exception:
        pass


app = FastAPI(
    title="LinkPlease Pseudogram Automation API",
    description="Production-quality backend for Instagram comment automation with idempotency, retries, and rate limiting.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rules.router)
app.include_router(webhook.router)
app.include_router(stats.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": "LinkPlease Pseudogram Automation System",
        "status": "online",
        "docs": "/docs"
    }
