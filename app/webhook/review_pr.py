from __future__ import annotations

import asyncio
from typing import Any, Protocol

import httpx

from devbrief_core.review import review_diff
from .fetch_diff import fetch_changed_files
from .line_map import build_line_map, find_nearest_valid_line


class InstallationClient(Protocol):
    async def get(self, path_or_url: str, **kwargs: object) -> httpx.Response: ...
    async def post(self, path_or_url: str, **kwargs: object) -> httpx.Response: ...


def _comment_body(issue: Any) -> str:
    body = f"❌ Issue: {issue.issue}\n📖 Why: {issue.why}\n✅ Fix: {issue.fix}"
    if issue.learn_more_url:
        body += f"\n🔗 Learn: {issue.learn_more_url}"
    return body


def _summary(issue_count: int, skipped_count: int, failed_files: list[dict[str, str]], fallback_notes: list[str]) -> str:
    if issue_count == 0 and not failed_files:
        return f"✅ DevBrief found no actionable issues. Skipped files: {skipped_count}."
    lines = [f"## DevBrief review", f"Issues found: {issue_count}", f"Skipped files: {skipped_count}", f"Failed files: {len(failed_files)}"]
    if failed_files:
        lines += ["", "### Failed files"] + [f"- `{item['file']}`: {item['reason']}" for item in failed_files]
    if fallback_notes:
        lines += ["", "### Notes that could not be placed inline"] + [f"- {note}" for note in fallback_notes]
    return "\n".join(lines)


async def review_pull_request(installation_client: InstallationClient, owner: str, repo: str, pull_number: int) -> None:
    changed = await fetch_changed_files(installation_client, owner, repo, pull_number)
    issue_comment_url = f"/repos/{owner}/{repo}/issues/{pull_number}/comments"
    if changed["too_large"]:
        response = await installation_client.post(issue_comment_url, json={"body": f"DevBrief skipped this pull request because it has more than 40 changed files (at least {changed['file_count']})."})
        response.raise_for_status()
        return

    semaphore = asyncio.Semaphore(5)
    failed_files: list[dict[str, str]] = []

    async def review_file(changed_file: dict[str, Any]) -> tuple[dict[str, Any], Any | None]:
        try:
            async with semaphore:
                return changed_file, await review_diff(changed_file["patch"], changed_file["filename"])
        except Exception as error:
            failed_files.append({"file": changed_file.get("filename", "unknown"), "reason": str(error)})
            return changed_file, None

    reviewed_files = await asyncio.gather(*(review_file(changed_file) for changed_file in changed["reviewable_files"]))
    inline_comments: list[dict[str, Any]] = []
    fallback_notes: list[str] = []
    issue_count = 0
    for changed_file, result in reviewed_files:
        if result is None:
            continue
        valid_lines = build_line_map(changed_file["patch"])
        for issue in result.review.issues:
            issue_count += 1
            line = find_nearest_valid_line(issue.start_line, valid_lines)
            if line is None:
                fallback_notes.append(f"`{issue.file}` line {issue.start_line}: {issue.issue}")
                continue
            inline_comments.append({"path": changed_file["filename"], "line": line, "side": "RIGHT", "body": _comment_body(issue)})

    pull_response = await installation_client.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
    pull_response.raise_for_status()
    head_sha = pull_response.json()["head"]["sha"]
    response = await installation_client.post(
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json={
            "commit_id": head_sha,
            "event": "COMMENT",
            "body": _summary(issue_count, len(changed["skipped_files"]), failed_files, fallback_notes),
            "comments": inline_comments,
        },
    )
    response.raise_for_status()

