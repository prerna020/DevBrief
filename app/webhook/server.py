from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

import asyncpg
import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

# pyrefly: ignore [missing-import]
from app.auth.oauth import router as auth_router

# pyrefly: ignore [missing-import]
from .rules_api import router as rules_router
# pyrefly: ignore [missing-import]
from .stats_api import router as stats_router

load_dotenv()

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
)
logger = structlog.get_logger(__name__)

app = FastAPI(title="DevBrief GitHub webhook")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rules_router)
app.include_router(stats_router)
app.include_router(auth_router, prefix="/auth")


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    return True


async def _record_delivery(delivery_id: str, log: Any) -> bool:
    """Record a delivery before scheduling work; False means it is a duplicate."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing. Webhook delivery de-duplication requires PostgreSQL.")
    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute("INSERT INTO processed_deliveries (delivery_id) VALUES ($1)", delivery_id)
        return True
    except asyncpg.exceptions.UniqueViolationError:
        log.info("Ignoring duplicate GitHub delivery")
        return False
    finally:
        await connection.close()

async def _enqueue_job(payload: dict[str, Any], delivery_id: str, log: Any) -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing. Review jobs require PostgreSQL.")
    connection = await asyncpg.connect(database_url)
    try:
        payload["X-GitHub-Delivery"] = delivery_id
        await connection.execute("INSERT INTO review_jobs (payload) VALUES ($1::jsonb)", json.dumps(payload))
        log.info("Enqueued review job")
    except Exception as e:
        log.exception("Failed to enqueue job", error=str(e), error_type=type(e).__name__)
        raise
    finally:
        await connection.close()

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(request: Request) -> dict[str, str]:
    raw_body = await request.body()
    if not _verify_signature(raw_body, request.headers.get("X-Hub-Signature-256")):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not delivery_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-GitHub-Delivery header")
        
    log = logger.bind(delivery_id=delivery_id)
    
    try:
        if not await _record_delivery(delivery_id, log):
            return {"status": "duplicate"}
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from error

        event, action = request.headers.get("X-GitHub-Event"), payload.get("action")
        log.info("Received webhook", github_event=event, action=action)
        if event != "pull_request" or action not in {"opened", "synchronize"}:
            log.info("Ignoring GitHub event", github_event=event, action=action)
            return {"status": "ignored"}
        
        payload["action"] = action
        await _enqueue_job(payload, delivery_id, log)
        return {"status": "accepted"}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Webhook handler error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e))

