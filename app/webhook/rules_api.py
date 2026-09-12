from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db.rules_repo import create_rule, delete_rule, list_rules, set_rule_active

# UNAUTHENTICATED, for local dev / Phase 3 dashboard wiring only, must add auth before any real deployment.
router = APIRouter()


class CreateRuleBody(BaseModel):
    rule_text: str
    category: str | None = None


class ToggleRuleBody(BaseModel):
    active: bool


async def get_connection() -> AsyncIterator[asyncpg.Connection]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing.")
    connection = await asyncpg.connect(database_url)
    try:
        yield connection
    finally:
        await connection.close()


@router.post("/teams/{team_id}/rules", status_code=status.HTTP_201_CREATED)
async def add_rule(team_id: int, body: CreateRuleBody, conn: asyncpg.Connection = Depends(get_connection)) -> dict[str, object]:
    return await create_rule(conn, team_id, body.rule_text, body.category)


@router.get("/teams/{team_id}/rules")
async def get_rules(team_id: int, conn: asyncpg.Connection = Depends(get_connection)) -> list[dict[str, object]]:
    return await list_rules(conn, team_id)


@router.patch("/rules/{rule_id}")
async def toggle_rule(rule_id: int, body: ToggleRuleBody, conn: asyncpg.Connection = Depends(get_connection)) -> dict[str, object]:
    rule = await set_rule_active(conn, rule_id, body.active)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_rule(rule_id: int, conn: asyncpg.Connection = Depends(get_connection)) -> None:
    if not await delete_rule(conn, rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
