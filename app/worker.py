import asyncio
import json
import os
from typing import Any

import asyncpg
import structlog
from dotenv import load_dotenv

from app.webhook.github_app import create_installation_client
from app.webhook.review_pr import review_pull_request

load_dotenv()

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
)
logger = structlog.get_logger(__name__)

async def process_job(conn: asyncpg.Connection, job_id: int, payload: dict[str, Any], log: Any) -> None:
    action = payload.get("action")
    installation_id = payload["installation"]["id"]
    repository = payload["repository"]
    pull_request = payload["pull_request"]
    owner, repo, number = repository["owner"]["login"], repository["name"], pull_request["number"]
    developer_login = pull_request["user"]["login"]
    
    client = await create_installation_client(installation_id)
    try:
        log.info("Starting review", owner=owner, repo=repo, number=number, action=action)
        await review_pull_request(client, owner, repo, number, developer_login, conn, action, log)
        await conn.execute("UPDATE review_jobs SET status = 'done' WHERE id = $1", job_id)
        log.info("Completed review", owner=owner, repo=repo, number=number)
    except Exception as e:
        log.exception("Review failed", owner=owner, repo=repo, number=number, error=str(e))
        await conn.execute(
            "UPDATE review_jobs SET status = 'failed' WHERE id = $1", job_id
        )
    finally:
        await client.aclose()

async def worker_loop() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing.")
    
    conn = await asyncpg.connect(database_url)
    logger.info("Worker started polling for review jobs...")
    try:
        while True:
            # We use a transaction for FOR UPDATE SKIP LOCKED
            async with conn.transaction():
                job = await conn.fetchrow("""
                    SELECT id, payload, attempts FROM review_jobs 
                    WHERE status = 'pending' OR (status = 'failed' AND attempts < 3)
                    ORDER BY id 
                    FOR UPDATE SKIP LOCKED 
                    LIMIT 1
                """)
                
                if job:
                    job_id = job["id"]
                    payload = json.loads(job["payload"])
                    attempts = job["attempts"] + 1
                    delivery_id = payload.get("X-GitHub-Delivery", "unknown")
                    log = logger.bind(delivery_id=delivery_id, job_id=job_id, attempts=attempts)
                    
                    await conn.execute("UPDATE review_jobs SET status = 'processing', attempts = $1 WHERE id = $2", attempts, job_id)
                    
                    # We process the job without holding the transaction open too long?
                    # The transaction keeps the lock until we commit. If processing takes 2 minutes, the transaction is held.
                    # A better way is to UPDATE and commit, then process outside.
                
            if job:
                # Process outside the row lock
                try:
                    await process_job(conn, job_id, payload, log)
                except Exception as e:
                    log.exception("Unhandled error processing job", error=str(e))
                    if attempts >= 3:
                        await conn.execute("UPDATE review_jobs SET status = 'dead' WHERE id = $1", job_id)
                    else:
                        await conn.execute("UPDATE review_jobs SET status = 'failed' WHERE id = $1", job_id)
            else:
                await asyncio.sleep(2)
                
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(worker_loop())
