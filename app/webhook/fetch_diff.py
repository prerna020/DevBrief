from __future__ import annotations

import re
from typing import Any, Protocol

import httpx

MAX_REVIEWABLE_FILES = 40


class InstallationClient(Protocol):
    async def get(self, path_or_url: str, **kwargs: object) -> httpx.Response: ...


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for url, relation in re.findall(r"<([^>]+)>;\s*rel=\"([^\"]+)\"", link_header):
        if relation == "next":
            return url
    return None


async def fetch_changed_files(
    installation_client: InstallationClient, owner: str, repo: str, pull_number: int
) -> dict[str, Any]:
    """Fetch at most 40 PR files, preserving binary/large files as skipped."""
    next_url: str | None = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
    params: dict[str, int] | None = {"per_page": 100}
    file_count = 0
    reviewable_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []

    while next_url:
        response = await installation_client.get(next_url, params=params)
        response.raise_for_status()
        files = response.json()
        if not isinstance(files, list):
            raise ValueError("GitHub files endpoint returned a non-list response.")
        for changed_file in files:
            file_count += 1
            if file_count > MAX_REVIEWABLE_FILES:
                return {"too_large": True, "file_count": file_count}
            if not changed_file.get("patch"):
                skipped_files.append({"file": changed_file.get("filename", "unknown"), "reason": "No patch returned (binary file or diff too large)."})
            else:
                reviewable_files.append(changed_file)
        next_url = _next_link(response.headers.get("Link"))
        params = None  # The Link URL already contains its own page parameters.

    return {"too_large": False, "file_count": file_count, "reviewable_files": reviewable_files, "skipped_files": skipped_files}

async def fetch_files_since(
    installation_client: InstallationClient, owner: str, repo: str, base_sha: str, head_sha: str
) -> dict[str, Any] | None:
    """Fetch files changed between base_sha and head_sha using /compare/{base}...{head}."""
    next_url: str | None = f"/repos/{owner}/{repo}/compare/{base_sha}...{head_sha}"
    params: dict[str, int] | None = {"per_page": 100}
    file_count = 0
    reviewable_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []

    try:
        while next_url:
            response = await installation_client.get(next_url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            
            files = data.get("files", [])
            for changed_file in files:
                file_count += 1
                if file_count > MAX_REVIEWABLE_FILES:
                    return {"too_large": True, "file_count": file_count}
                if not changed_file.get("patch"):
                    skipped_files.append({"file": changed_file.get("filename", "unknown"), "reason": "No patch returned (binary file or diff too large)."})
                else:
                    reviewable_files.append(changed_file)
            
            next_url = _next_link(response.headers.get("Link"))
            params = None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise
    except Exception:
        return None

    return {"too_large": False, "file_count": file_count, "reviewable_files": reviewable_files, "skipped_files": skipped_files}
