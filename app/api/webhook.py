import json
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.mongodb import get_database
from app.services.webhook_service import WebhookService
from app.utils.signatures import verify_hmac_signature

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Webhook"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_webhook(
    request: Request,
    x_pseudogram_signature: str = Header(None, alias="X-PseudoGram-Signature"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    raw_body = await request.body()

    # Part B: Webhook Signature Verification
    if settings.WEBHOOK_SIGNATURE_REQUIRED:
        if not x_pseudogram_signature:
            logger.warning("Webhook request rejected: missing X-PseudoGram-Signature header.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature header"
            )

        if not verify_hmac_signature(raw_body, settings.PSEUDOGRAM_API_KEY, x_pseudogram_signature):
            logger.warning("Webhook request rejected: invalid HMAC signature.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(exc)}"
        )

    service = WebhookService(db)
    result = await service.process_incoming_event(payload)
    return result
