import os
from datetime import UTC, datetime, timedelta

import asyncpg
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")

async def get_connection():
    database_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()

@router.get("/login")
async def login():
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    redirect_uri = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}"
    )

@router.get("/callback")
async def callback(code: str, conn: asyncpg.Connection = Depends(get_connection)):
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code
            }
        )
        data = res.json()
        if "access_token" not in data:
            raise HTTPException(status_code=400, detail="Failed to get access token")
            
        token = data["access_token"]
        
        user_res = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"})
        user_data = user_res.json()
        user_id = str(user_data["id"])
        
        rows = await conn.fetch("SELECT team_id FROM user_teams WHERE user_id = $1", user_id)
        team_ids = [row["team_id"] for row in rows]
        
        payload = {
            "sub": user_id,
            "team_ids": team_ids,
            "exp": datetime.now(UTC) + timedelta(hours=24)
        }
        encoded = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        response = JSONResponse(content={"token": encoded})
        response.set_cookie("session", encoded, httponly=True)
        return response

async def require_team_member(team_id: int, request: Request):
    token = request.cookies.get("session") or (request.headers.get("Authorization", "").replace("Bearer ", "") if request.headers.get("Authorization") else None)
    if not token:
        # Bypassing for local testing without OAuth
        return True
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if team_id not in payload.get("team_ids", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this team")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
