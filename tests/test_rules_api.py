from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.webhook import rules_api, server


class FakeRulesDatabase:
    def __init__(self) -> None:
        self.rules: dict[int, dict[str, object]] = {}
        self.next_id = 1

    async def fetchrow(self, query: str, *args: object):
        if query.startswith("INSERT INTO rules"):
            rule = {"id": self.next_id, "team_id": args[0], "rule_text": args[1], "category": args[2], "active": True, "created_at": "2026-01-01T00:00:00Z"}
            self.rules[self.next_id] = rule
            self.next_id += 1
            return rule
        if query.startswith("UPDATE rules"):
            rule = self.rules.get(args[0])
            if rule is not None:
                rule["active"] = args[1]
            return rule
        raise AssertionError(f"Unexpected fetchrow: {query}")

    async def fetch(self, query: str, *args: object):
        assert "active = true" in query
        return [rule for rule in self.rules.values() if rule["team_id"] == args[0] and rule["active"] is True]

    async def execute(self, query: str, *args: object) -> str:
        if query.startswith("DELETE FROM rules"):
            return "DELETE 1" if self.rules.pop(args[0], None) else "DELETE 0"
        raise AssertionError(f"Unexpected execute: {query}")

    async def close(self) -> None:
        pass


def test_create_list_and_toggle_rule_inactive() -> None:
    database = FakeRulesDatabase()

    async def override_connection() -> AsyncIterator[FakeRulesDatabase]:
        yield database

    server.app.dependency_overrides[rules_api.get_connection] = override_connection
    try:
        with TestClient(server.app) as client:
            created = client.post("/teams/5/rules", json={"rule_text": "Use parameterized SQL queries", "category": "security"})
            assert created.status_code == 201
            rule_id = created.json()["id"]
            assert client.get("/teams/5/rules").json()[0]["rule_text"] == "Use parameterized SQL queries"
            assert client.patch(f"/rules/{rule_id}", json={"active": False}).json()["active"] is False
            assert client.get("/teams/5/rules").json() == []
    finally:
        server.app.dependency_overrides.clear()
