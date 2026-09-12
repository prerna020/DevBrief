from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.review import ReviewError, review_diff
from app.core.schema import Issue
from app.core.prompts.learning_mode_v1 import build_learning_mode_prompt


def completion(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def client_with(create: AsyncMock) -> SimpleNamespace:
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.review.asyncio.sleep", AsyncMock())


@pytest.mark.asyncio
async def test_valid_mocked_response_parses_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    create = AsyncMock(return_value=completion(json.dumps({"issues": [{"file": "app.py", "startLine": 1, "category": "security", "severity": "high", "issue": "Unsafe input", "why": "Input must be validated", "fix": "Validate it.", "matchedRule": None}]})))
    monkeypatch.setattr("app.core.review.create_groq_client", lambda: client_with(create))

    result = await review_diff("+dangerous(input)", "app.py")

    assert result.review.issues[0].issue == "Unsafe input"
    assert result.usage.total_tokens == 15
    assert create.await_count == 1


@pytest.mark.asyncio
async def test_team_rules_are_sent_in_the_groq_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    rule = "Use parameterized SQL queries"
    create = AsyncMock(return_value=completion(json.dumps({"issues": []})))
    monkeypatch.setattr("app.core.review.create_groq_client", lambda: client_with(create))

    await review_diff("+cursor.execute(query)", "db.py", [rule])

    system_prompt = create.await_args.kwargs["messages"][0]["content"]
    assert "TEAM RULES" in system_prompt
    assert rule in system_prompt


def test_matched_rule_is_required_and_team_prompt_preserves_exact_rule() -> None:
    assert "matchedRule" in Issue.model_json_schema()["required"]
    rule = "All database calls must have a timeout"
    prompt = build_learning_mode_prompt([rule])
    assert "TEAM RULES" in prompt
    assert rule in prompt
    assert "exact rule text" in prompt


@pytest.mark.asyncio
async def test_malformed_json_retries_then_raises_review_error(monkeypatch: pytest.MonkeyPatch) -> None:
    create = AsyncMock(return_value=completion("not json"))
    monkeypatch.setattr("app.core.review.create_groq_client", lambda: client_with(create))

    with pytest.raises(ReviewError):
        await review_diff("diff", "app.py")

    assert create.await_count == 3


@pytest.mark.asyncio
async def test_missing_required_field_retries_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    create = AsyncMock(return_value=completion(json.dumps({"issues": [{"file": "app.py", "startLine": 1, "category": "security", "severity": "high", "issue": "Unsafe input", "why": "Input must be validated"}]})))
    monkeypatch.setattr("app.core.review.create_groq_client", lambda: client_with(create))

    with pytest.raises(ReviewError):
        await review_diff("diff", "app.py")

    assert create.await_count == 3
