from __future__ import annotations

from typing import Protocol


class AsyncpgConnection(Protocol):
    async def fetchrow(self, query: str, *args: object) -> object: ...
    async def fetchval(self, query: str, *args: object) -> object: ...
    async def fetch(self, query: str, *args: object) -> list[object]: ...
    async def execute(self, query: str, *args: object) -> str: ...


def _value(row: object, key: str) -> object:
    """Read an asyncpg Record or mapping without tying the code to either type."""
    return row[key]  # type: ignore[index]


async def get_or_create_team_and_repo(conn: AsyncpgConnection, owner: str, name: str) -> tuple[int, int]:
    existing_repo = await conn.fetchrow(
        "SELECT id, team_id FROM repos WHERE owner = $1 AND name = $2", owner, name
    )
    if existing_repo is not None:
        return int(_value(existing_repo, "team_id")), int(_value(existing_repo, "id"))

    created_team = await conn.fetchrow(
        "INSERT INTO teams (name) VALUES ($1) RETURNING id", f"{owner}/{name} (auto)"
    )
    if created_team is None:
        raise RuntimeError("Creating the automatic team returned no row.")
    team_id = int(_value(created_team, "id"))
    created_repo = await conn.fetchrow(
        "INSERT INTO repos (team_id, owner, name) VALUES ($1, $2, $3) RETURNING id", team_id, owner, name
    )
    if created_repo is None:
        raise RuntimeError("Creating the automatic repo returned no row.")
    repo_id = int(_value(created_repo, "id"))
    return team_id, repo_id


async def get_active_rules(conn: AsyncpgConnection, team_id: int) -> list[str]:
    rows = await conn.fetch(
        "SELECT rule_text FROM rules WHERE team_id = $1 AND active = true ORDER BY created_at",
        team_id,
    )
    return [str(_value(row, "rule_text")) for row in rows]


async def create_rule(conn: AsyncpgConnection, team_id: int, rule_text: str, category: str | None) -> dict[str, object]:
    row = await conn.fetchrow(
        "INSERT INTO rules (team_id, rule_text, category) VALUES ($1, $2, $3) RETURNING id, team_id, rule_text, category, active, created_at",
        team_id, rule_text, category,
    )
    if row is None:
        raise RuntimeError("Creating rule returned no row.")
    return dict(row)  # type: ignore[arg-type]


async def list_rules(conn: AsyncpgConnection, team_id: int) -> list[dict[str, object]]:
    rows = await conn.fetch("SELECT id, team_id, rule_text, category, active, created_at FROM rules WHERE team_id = $1 AND active = true ORDER BY created_at", team_id)
    return [dict(row) for row in rows]  # type: ignore[arg-type]


async def set_rule_active(conn: AsyncpgConnection, rule_id: int, active: bool) -> dict[str, object] | None:
    row = await conn.fetchrow("UPDATE rules SET active = $2 WHERE id = $1 RETURNING id, team_id, rule_text, category, active, created_at", rule_id, active)
    return None if row is None else dict(row)  # type: ignore[arg-type]


async def delete_rule(conn: AsyncpgConnection, rule_id: int) -> bool:
    result = await conn.execute("DELETE FROM rules WHERE id = $1", rule_id)
    return result != "DELETE 0"
