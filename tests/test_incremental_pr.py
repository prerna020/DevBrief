from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.schema import Issue
from app.webhook import review_pr
from tests.test_review_pr import (
    FakeInstallationClient,
    FakeRulesConnection,
    review_result,
)


@pytest.mark.asyncio
async def test_incremental_review_resolves_issue(monkeypatch, client: FakeInstallationClient) -> None:
    async def fake_diff(file, new_issues, prev_unresolved):
        return {"resolved": prev_unresolved, "still_present": [], "new": new_issues}
        
    monkeypatch.setattr("app.webhook.resolution.diff_against_previous", AsyncMock(side_effect=fake_diff))
    monkeypatch.setattr(review_pr, "review_diff", AsyncMock(return_value=review_result()))

    class IncrementalFakeRulesConnection(FakeRulesConnection):
        async def fetchrow(self, query: str, *args: object):
            if query.startswith("SELECT last_reviewed_sha"):
                return {"last_reviewed_sha": "old-sha"}
            return await super().fetchrow(query, *args)
            
        async def fetch(self, query: str, *args: object):
            if "SELECT i.id, i.file" in query:
                return [{"id": 100, "file": "unsafe.py", "category": "security", "severity": "high", "is_custom_rule_violation": False, "matched_rule": None, "issue": "old issue", "why": "", "fix": ""}]
            return await super().fetch(query, *args)
            
    conn = IncrementalFakeRulesConnection()
    await review_pr.review_pull_request(client, "acme", "demo", 7, "dev123", conn, "synchronize")
    
    payload = client.posts[-1][1]
    assert "✅ Fixed 1 issue(s)" in payload["body"]
    assert any("UPDATE review_issues SET resolved = true" in q for q in conn.executed)

@pytest.mark.asyncio
async def test_incremental_review_still_present_and_new(monkeypatch, client: FakeInstallationClient) -> None:
    async def fake_diff(file, new_issues, prev_unresolved):
        return {"resolved": [], "still_present": prev_unresolved, "new": new_issues}
        
    monkeypatch.setattr("app.webhook.resolution.diff_against_previous", AsyncMock(side_effect=fake_diff))
    
    issue = Issue(file="unsafe.py", startLine=2, category="security", severity="high", issue="New bug", why="Input is untrusted", fix="Validate it.", matchedRule=None)
    monkeypatch.setattr(review_pr, "review_diff", AsyncMock(return_value=review_result(issue)))

    class IncrementalFakeRulesConnection(FakeRulesConnection):
        async def fetchrow(self, query: str, *args: object):
            if query.startswith("SELECT last_reviewed_sha"):
                return {"last_reviewed_sha": "old-sha"}
            return await super().fetchrow(query, *args)
            
        async def fetch(self, query: str, *args: object):
            if "SELECT i.id, i.file" in query:
                return [{"id": 100, "file": "unsafe.py", "category": "security", "severity": "high", "is_custom_rule_violation": False, "matched_rule": None, "issue": "old issue", "why": "", "fix": ""}]
            return await super().fetch(query, *args)
            
    conn = IncrementalFakeRulesConnection()
    await review_pr.review_pull_request(client, "acme", "demo", 7, "dev123", conn, "synchronize")
    
    payload = client.posts[-1][1]
    assert "⚠️ 1 still present" in payload["body"]
    assert "❌ 1 new issue(s)" in payload["body"]
    assert len(payload["comments"]) == 1
    assert "New bug" in payload["comments"][0]["body"]
    assert len(conn.inserted_review_issues) == 1

@pytest.mark.asyncio
async def test_incremental_review_force_push_fallback(monkeypatch, client: FakeInstallationClient) -> None:
    monkeypatch.setattr(review_pr, "review_diff", AsyncMock(return_value=review_result()))

    class IncrementalFakeRulesConnection(FakeRulesConnection):
        async def fetchrow(self, query: str, *args: object):
            if query.startswith("SELECT last_reviewed_sha"):
                return {"last_reviewed_sha": "force-push-old"}
            return await super().fetchrow(query, *args)
            
    conn = IncrementalFakeRulesConnection()
    await review_pr.review_pull_request(client, "acme", "demo", 7, "dev123", conn, "synchronize")
    
    payload = client.posts[-1][1]
    assert "DevBrief found no actionable issues" in payload["body"]
