import asyncio
from unittest.mock import AsyncMock

import pytest

from app import worker


class FakeWorkerDB:
    def __init__(self):
        self.jobs = [
            {"id": 1, "payload": '{"X-GitHub-Delivery": "d1"}', "status": "pending", "attempts": 0},
            {"id": 2, "payload": '{"X-GitHub-Delivery": "d2"}', "status": "pending", "attempts": 0},
            {"id": 3, "payload": '{"X-GitHub-Delivery": "d3"}', "status": "pending", "attempts": 0},
            {"id": 4, "payload": '{"X-GitHub-Delivery": "d4"}', "status": "pending", "attempts": 0},
            {"id": 5, "payload": '{"X-GitHub-Delivery": "d5"}', "status": "pending", "attempts": 0},
        ]
        self.lock = asyncio.Lock()
        self.processed = []
        
    def transaction(self):
        class DummyTransaction:
            async def __aenter__(self): pass
            async def __aexit__(self, exc_type, exc, tb): pass
        return DummyTransaction()
        
    async def fetchrow(self, query: str, *args):
        # Simulate SKIP LOCKED
        async with self.lock:
            for job in self.jobs:
                if job["status"] == "pending":
                    job["status"] = "processing_lock"
                    return job
            return None

    async def execute(self, query: str, *args):
        if query.startswith("UPDATE review_jobs SET status = 'processing'") or query.startswith("UPDATE review_jobs SET status = 'done'"):
            pass
            
    async def close(self):
        pass

@pytest.mark.asyncio
async def test_worker_skip_locked(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://fake")
    db = FakeWorkerDB()
    monkeypatch.setattr(worker.asyncpg, "connect", AsyncMock(return_value=db))
    
    processed_jobs = []
    
    orig_sleep = asyncio.sleep
    async def mock_process(conn, job_id, payload, log):
        await orig_sleep(0.01)
        processed_jobs.append(job_id)

    monkeypatch.setattr(worker, "process_job", mock_process)
    
    class StopLoop(Exception): pass
    async def fake_sleep(*args): raise StopLoop()
    monkeypatch.setattr(worker.asyncio, "sleep", fake_sleep)
    
    # Run two workers concurrently
    results = await asyncio.gather(worker.worker_loop(), worker.worker_loop(), return_exceptions=True)
    
    # Both should have exited with StopLoop
    for res in results:
        assert isinstance(res, StopLoop)
        
    assert sorted(processed_jobs) == [1, 2, 3, 4, 5]
    assert len(processed_jobs) == 5
