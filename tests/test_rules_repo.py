from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.db.rules_repo import get_active_rules, get_or_create_team_and_repo


@pytest.mark.asyncio
async def test_active_rules_excludes_inactive_rules() -> None:
    conn = AsyncMock()
    # The mocked database only returns active rows, as the repository query requires.
    conn.fetch.return_value = [{"rule_text": "Reject SQL built with string concatenation"}]

    rules = await get_active_rules(conn, 7)

    assert rules == ["Reject SQL built with string concatenation"]
    query, team_id = conn.fetch.await_args.args
    assert "active = true" in query
    assert "ORDER BY created_at" in query
    assert team_id == 7


@pytest.mark.asyncio
async def test_new_repo_gets_an_automatic_team() -> None:
    conn = AsyncMock()
    conn.fetchrow.side_effect = [None, {"id": 42}, {"id": 99}]

    team_id, repo_id = await get_or_create_team_and_repo(conn, "acme", "widget")

    assert team_id == 42
    assert repo_id == 99
