from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.webhook import review_pr
from app.core.review import ReviewResult, TokenUsage
from app.core.schema import Issue, Review


FILES = [
    {"filename": "unsafe.py", "patch": "@@ -1,2 +1,3 @@\n context\n+dangerous(user_input)\n clean"},
    {"filename": "image.png", "status": "modified"},
    {"filename": "clean.py", "patch": "@@ -10,1 +10,1 @@\n unchanged"},
]


def response(payload: object) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://api.github.test"))


class FakeInstallationClient:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []

    async def get(self, path: str, **_: object) -> httpx.Response:
        if path.endswith("/files"):
            return response(FILES)
        if "/pulls/7" in path:
            return response({"head": {"sha": "head-sha"}})
        raise AssertionError(f"Unexpected GET {path}")

    async def post(self, path: str, **kwargs: object) -> httpx.Response:
        self.posts.append((path, kwargs["json"]))  # type: ignore[index]
        return response({"id": 1})


class FakeRulesConnection:
    async def fetchrow(self, query: str, *_: object):
        if query.startswith("SELECT team_id"):
            return {"team_id": 9}
        raise AssertionError(f"Unexpected fetchrow: {query}")

    async def fetch(self, query: str, *_: object):
        assert "active = true" in query
        return [{"rule_text": "Use parameterized SQL queries"}]

    async def execute(self, *_: object):
        raise AssertionError("The existing repository should not be created again")


def review_result(*issues: Issue) -> ReviewResult:
    return ReviewResult(Review(issues=list(issues)), TokenUsage(1, 1, 2), 1.0, 1)


@pytest.fixture
def client() -> FakeInstallationClient:
    return FakeInstallationClient()


@pytest.mark.asyncio
async def test_binary_is_skipped_and_issue_is_mapped_inline(monkeypatch, client: FakeInstallationClient) -> None:
    issue = Issue(file="unsafe.py", startLine=2, category="security", severity="high", issue="Unsafe input", why="Input is untrusted", fix="Validate it.", matchedRule=None)
    mocked_review = AsyncMock(side_effect=lambda _patch, path, _rules: review_result(issue) if path == "unsafe.py" else review_result())
    monkeypatch.setattr(review_pr, "review_diff", mocked_review)

    await review_pr.review_pull_request(client, "acme", "demo", 7, FakeRulesConnection())

    reviewed_paths = {call.args[1] for call in mocked_review.await_args_list}
    assert reviewed_paths == {"unsafe.py", "clean.py"}  # image.png has no patch and is never reviewed.
    assert all(call.args[2] == ["Use parameterized SQL queries"] for call in mocked_review.await_args_list)
    payload = client.posts[-1][1]
    assert payload["comments"] == [{"path": "unsafe.py", "line": 2, "side": "RIGHT", "body": "❌ Issue: Unsafe input\n📖 Why: Input is untrusted\n✅ Fix: Validate it."}]
    assert "Skipped files: 1" in payload["body"]


@pytest.mark.asyncio
async def test_zero_issues_still_posts_positive_summary(monkeypatch, client: FakeInstallationClient) -> None:
    monkeypatch.setattr(review_pr, "review_diff", AsyncMock(return_value=review_result()))

    await review_pr.review_pull_request(client, "acme", "demo", 7, FakeRulesConnection())

    payload = client.posts[-1][1]
    assert payload["comments"] == []
    assert "no actionable issues" in payload["body"]
    assert payload["body"]


@pytest.mark.asyncio
async def test_one_review_failure_does_not_stop_other_files(monkeypatch, client: FakeInstallationClient) -> None:
    async def review_side_effect(_: str, path: str, _rules: list[str]) -> ReviewResult:
        if path == "unsafe.py":
            raise RuntimeError("model unavailable")
        return review_result()

    mocked_review = AsyncMock(side_effect=review_side_effect)
    monkeypatch.setattr(review_pr, "review_diff", mocked_review)

    await review_pr.review_pull_request(client, "acme", "demo", 7, FakeRulesConnection())

    assert {call.args[1] for call in mocked_review.await_args_list} == {"unsafe.py", "clean.py"}
    assert "Failed files: 1" in client.posts[-1][1]["body"]


def test_custom_rule_comment_has_distinct_header() -> None:
    issue = Issue(file="unsafe.py", startLine=2, category="security", severity="high", issue="Unsafe input", why="Input is untrusted", fix="Validate it.", isCustomRuleViolation=True, matchedRule="Use parameterized SQL queries")
    assert review_pr._comment_body(issue).startswith("⚙️ Team rule: Use parameterized SQL queries\n❌ Issue:")
