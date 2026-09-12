from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.webhook.server import app

client = TestClient(app)

class FakeConnection:
    async def fetch(self, query: str, *args: object):
        if "GROUP BY created_at::date" in query:
            return [{"date": "2026-09-01", "count": 5}, {"date": "2026-09-02", "count": 3}]
        if "GROUP BY category" in query:
            return [{"category": "security", "count": 10}, {"category": "performance", "count": 2}]
        if "GROUP BY r.developer_login" in query:
            return [{"developer_login": "alice", "prs_reviewed": 5, "total_issues": 15}]
        raise AssertionError(f"Unexpected query: {query}")

    async def close(self):
        pass

@pytest.fixture
def mock_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://fake")
    import asyncpg
    monkeypatch.setattr(asyncpg, "connect", AsyncMock(return_value=FakeConnection()))

def test_stats_trends(mock_db):
    response = client.get("/teams/1/stats/trends?days=7")
    assert response.status_code == 200
    assert response.json() == [{"date": "2026-09-01", "count": 5}, {"date": "2026-09-02", "count": 3}]

def test_stats_categories(mock_db):
    response = client.get("/teams/1/stats/categories")
    assert response.status_code == 200
    assert response.json() == [{"category": "security", "count": 10}, {"category": "performance", "count": 2}]

def test_leaderboard(mock_db):
    response = client.get("/teams/1/leaderboard")
    assert response.status_code == 200
    assert response.json() == [{"developer_login": "alice", "prs_reviewed": 5, "total_issues": 15}]
