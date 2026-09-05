"""GitHub App authentication using the PyJWT/httpx fallback.

githubkit is not a dependency of this project, so its App-auth strategy types
are unavailable to inspect. This module uses GitHub's documented JWT and
installation-token exchange instead.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx
import jwt
from dotenv import load_dotenv

load_dotenv()

GITHUB_API_URL = "https://api.github.com"


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file.")
    return value


def github_app_jwt() -> str:
    """Create the short-lived RS256 JWT GitHub requires for an app."""
    app_id = _required_environment("GITHUB_APP_ID")
    private_key = _required_environment("GITHUB_PRIVATE_KEY").replace("\\n", "\n")
    now = int(time.time())
    return jwt.encode({"iat": now - 60, "exp": now + 600, "iss": app_id}, private_key, algorithm="RS256")


@dataclass
class InstallationClient:
    """Small async GitHub client authenticated as one installation."""

    client: httpx.AsyncClient

    async def get(self, path_or_url: str, **kwargs: object) -> httpx.Response:
        return await self.client.get(path_or_url, **kwargs)

    async def post(self, path_or_url: str, **kwargs: object) -> httpx.Response:
        return await self.client.post(path_or_url, **kwargs)

    async def aclose(self) -> None:
        await self.client.aclose()


async def create_installation_client(installation_id: int) -> InstallationClient:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_app_jwt()}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(base_url=GITHUB_API_URL, headers=headers, timeout=20.0) as app_client:
        response = await app_client.post(f"/app/installations/{installation_id}/access_tokens")
        response.raise_for_status()
        token = response.json()["token"]
    installation_client = httpx.AsyncClient(
        base_url=GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20.0,
    )
    return InstallationClient(installation_client)
