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

from devbrief_core.review import review_diff
from .fetch_diff import fetch_changed_files
from .github_app import create_installation_client

load_dotenv()
logger = logging.getLogger(__name__)
app = FastAPI(title="DevBrief GitHub webhook")


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret or not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _review_pull_request(payload: dict[str, Any]) -> None:
    installation_id = payload["installation"]["id"]
    repository = payload["repository"]
    pull_request = payload["pull_request"]
    owner, repo, number = repository["owner"]["login"], repository["name"], pull_request["number"]
    client = await create_installation_client(installation_id)
    try:
        changed = await fetch_changed_files(client, owner, repo, number)
        if changed["too_large"]:
            logger.info("Skipping %s/%s#%s: %s changed files exceeds cap", owner, repo, number, changed["file_count"])
            return
        for changed_file in changed["reviewable_files"]:
            await review_diff(changed_file["patch"], changed_file["filename"])
        logger.info("Reviewed %s files for %s/%s#%s; skipped %s", len(changed["reviewable_files"]), owner, repo, number, len(changed["skipped_files"]))
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

