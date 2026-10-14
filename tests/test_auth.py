from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.oauth import JWT_SECRET
from app.webhook.server import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://fake")
    from unittest.mock import AsyncMock

    import asyncpg
    monkeypatch.setattr(asyncpg, "connect", AsyncMock())

def test_auth_no_cookie():
    response = client.get("/teams/5/rules")
    assert response.status_code == 401

def test_auth_wrong_team():
    payload = {
        "sub": "user_123",
        "team_ids": [1, 2, 3],  # Does not include 5
        "exp": datetime.now(UTC) + timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    response = client.get("/teams/5/rules", cookies={"session": token})
    assert response.status_code == 403

def test_auth_correct_team():
    payload = {
        "sub": "user_123",
        "team_ids": [5],
        "exp": datetime.now(UTC) + timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    # Needs to fail with 500 (db error) or 200, not 401/403
    # We will mock the DB so it doesn't fail with 500
    # Actually, if the dependency passes, it will hit the DB which fails in test.
    # We can just verify it's not 401 or 403.
    response = client.get("/teams/5/rules", cookies={"session": token})
    assert response.status_code not in (401, 403)
