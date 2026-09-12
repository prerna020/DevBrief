from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
import asyncpg

from .github_app import create_installation_client
from .review_pr import review_pull_request
from .rules_api import router as rules_router

from fastapi.middleware.cors import CORSMiddleware
from .stats_api import router as stats_router

load_dotenv()
logger = logging.getLogger(__name__)
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


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret or not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _record_delivery(delivery_id: str) -> bool:
    """Record a delivery before scheduling work; False means it is a duplicate."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing. Webhook delivery de-duplication requires PostgreSQL.")
    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute("INSERT INTO processed_deliveries (delivery_id) VALUES ($1)", delivery_id)
        return True
    except asyncpg.exceptions.UniqueViolationError:
        logger.info("Ignoring duplicate GitHub delivery %s", delivery_id)
        return False
    finally:
        await connection.close()


async def _review_pull_request(payload: dict[str, Any]) -> None:
    installation_id = payload["installation"]["id"]
    repository = payload["repository"]
    pull_request = payload["pull_request"]
    owner, repo, number = repository["owner"]["login"], repository["name"], pull_request["number"]
    developer_login = pull_request["user"]["login"]
    client = await create_installation_client(installation_id)
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is missing. Team rules require PostgreSQL.")
        connection = await asyncpg.connect(database_url)
        try:
            await review_pull_request(client, owner, repo, number, developer_login, connection)
        finally:
            await connection.close()
        logger.info("Completed background review for %s/%s#%s", owner, repo, number)
    except Exception:
        logger.exception("Background review failed for %s/%s#%s", owner, repo, number)
    finally:
        await client.aclose()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def webhook(request: Request) -> dict[str, str]:
    raw_body = await request.body()  # Must occur before JSON parsing.
    if not _verify_signature(raw_body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not delivery_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-GitHub-Delivery header")
    if not await _record_delivery(delivery_id):
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "duplicate"})
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from error

    event, action = request.headers.get("X-GitHub-Event"), payload.get("action")
    if event != "pull_request" or action not in {"opened", "synchronize"}:
        logger.info("Ignoring GitHub event=%s action=%s", event, action)
        return {"status": "ignored"}
    asyncio.create_task(_review_pull_request(payload))
    return {"status": "accepted"}
