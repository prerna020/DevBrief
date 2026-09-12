from __future__ import annotations

import hashlib
import hmac

from fastapi.testclient import TestClient

from app.webhook import server


def _record_delivery() -> bool:
    return True


def test_health() -> None:
    with TestClient(server.app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_webhook_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    with TestClient(server.app) as client:
        response = client.post("/webhook", content=b'{"action":"opened"}', headers={"X-Hub-Signature-256": "sha256=invalid"})
    assert response.status_code == 401


def test_webhook_returns_before_background_review(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    async def record_delivery(_: str) -> bool: return True
    monkeypatch.setattr(server, "_record_delivery", record_delivery)
    body = b'{"action":"opened"}'
    signature = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    scheduled = []
    monkeypatch.setattr(server.asyncio, "create_task", lambda coroutine: (coroutine.close(), scheduled.append(True)))
    with TestClient(server.app) as client:
        response = client.post("/webhook", content=body, headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": signature, "X-GitHub-Delivery": "delivery-1"})
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert scheduled == [True]
