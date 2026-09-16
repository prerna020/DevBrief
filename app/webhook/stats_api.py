from __future__ import annotations

import os

import asyncpg
from fastapi import APIRouter, Depends

from app.auth.oauth import require_team_member

router = APIRouter(prefix="/teams/{team_id}", tags=["stats"])

@router.get("/stats/trends", dependencies=[Depends(require_team_member)])
async def get_trends(team_id: int, days: int = 30) -> list[dict[str, object]]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []
    connection = await asyncpg.connect(database_url)
    try:
        rows = await connection.fetch("""
            SELECT created_at::date as date, count(*) as count
            FROM review_issues
            WHERE review_id IN (SELECT id FROM reviews WHERE team_id = $1)
              AND created_at >= now() - interval '1 day' * $2
            GROUP BY created_at::date
            ORDER BY created_at::date
        """, team_id, days)
        return [{"date": str(r["date"]), "count": r["count"]} for r in rows]
    finally:
        await connection.close()

@router.get("/stats/categories", dependencies=[Depends(require_team_member)])
async def get_categories(team_id: int) -> list[dict[str, object]]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []
    connection = await asyncpg.connect(database_url)
    try:
        rows = await connection.fetch("""
            SELECT category, count(*) as count
            FROM review_issues
            WHERE review_id IN (SELECT id FROM reviews WHERE team_id = $1)
            GROUP BY category
            ORDER BY count DESC
        """, team_id)
        return [{"category": r["category"], "count": r["count"]} for r in rows]
    finally:
        await connection.close()

@router.get("/leaderboard", dependencies=[Depends(require_team_member)])
async def get_leaderboard(team_id: int) -> list[dict[str, object]]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return []
    connection = await asyncpg.connect(database_url)
    try:
        rows = await connection.fetch("""
            SELECT r.developer_login,
                   count(distinct r.id) as prs_reviewed,
                   count(ri.id) as total_issues
            FROM reviews r
            LEFT JOIN review_issues ri ON r.id = ri.review_id
            WHERE r.team_id = $1
            GROUP BY r.developer_login
            ORDER BY total_issues ASC
        """, team_id)
        return [{"developer_login": r["developer_login"], "prs_reviewed": r["prs_reviewed"], "total_issues": r["total_issues"]} for r in rows]
    finally:
        await connection.close()

@router.get("/stats/usage", dependencies=[Depends(require_team_member)])
async def get_usage(team_id: int) -> dict[str, object]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {}
    connection = await asyncpg.connect(database_url)
    try:
        row = await connection.fetchrow("""
            SELECT 
                SUM(estimated_cost_usd) as total_cost_month,
                AVG(prompt_tokens + completion_tokens) as avg_tokens_per_review
            FROM reviews
            WHERE team_id = $1
              AND created_at >= date_trunc('month', now())
        """, team_id)
        
        return {
            "total_cost_this_month": float(row["total_cost_month"] or 0),
            "average_tokens_per_review": float(row["avg_tokens_per_review"] or 0)
        }
    finally:
        await connection.close()
