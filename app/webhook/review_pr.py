from __future__ import annotations

import asyncio
from typing import Any, Protocol

import httpx

from app.core.review import review_diff
from app.db.rules_repo import (
    AsyncpgConnection,
    get_active_rules,
    get_or_create_team_and_repo,
)

from .line_map import build_line_map, find_nearest_valid_line


class InstallationClient(Protocol):
    async def get(self, path_or_url: str, **kwargs: object) -> httpx.Response: ...
    async def post(self, path_or_url: str, **kwargs: object) -> httpx.Response: ...


def _comment_body(issue: Any) -> str:
    prefix = f"⚙️ Team rule: {issue.matched_rule}\n" if issue.is_custom_rule_violation else ""
    body = f"{prefix}❌ Issue: {issue.issue}\n📖 Why: {issue.why}\n✅ Fix: {issue.fix}"
    if issue.learn_more_url:
        body += f"\n🔗 Learn: {issue.learn_more_url}"
    return body


def _summary(issue_count: int, skipped_count: int, failed_files: list[dict[str, str]], fallback_notes: list[str]) -> str:
    if issue_count == 0 and not failed_files:
        return f"✅ DevBrief found no actionable issues. Skipped files: {skipped_count}."
    lines = ["## DevBrief review", f"Issues found: {issue_count}", f"Skipped files: {skipped_count}", f"Failed files: {len(failed_files)}"]
    if failed_files:
        lines += ["", "### Failed files"] + [f"- `{item['file']}`: {item['reason']}" for item in failed_files]
    if fallback_notes:
        lines += ["", "### Notes that could not be placed inline"] + [f"- {note}" for note in fallback_notes]
    return "\n".join(lines)


def _incremental_summary(fixed_count: int, still_present_issues: list[dict], new_count: int, skipped_count: int, failed_files: list[dict[str, str]], fallback_notes: list[str]) -> str:
    lines = ["## DevBrief incremental review"]
    if fixed_count > 0:
        lines.append(f"✅ Fixed {fixed_count} issue(s)")
    if still_present_issues:
        lines.append(f"⚠️ {len(still_present_issues)} still present")
        for issue in still_present_issues:
            lines.append(f"- `{issue['file']}`: {issue['issue']}")
    if new_count > 0:
        lines.append(f"❌ {new_count} new issue(s)")
    if fixed_count == 0 and not still_present_issues and new_count == 0:
        lines.append("✅ No actionable issues in this update.")
    if skipped_count > 0:
        lines.append(f"Skipped files: {skipped_count}")
    if failed_files:
        lines += ["", "### Failed files"] + [f"- `{item['file']}`: {item['reason']}" for item in failed_files]
    if fallback_notes:
        lines += ["", "### Notes that could not be placed inline"] + [f"- {note}" for note in fallback_notes]
    return "\n".join(lines)


async def review_pull_request(installation_client: InstallationClient, owner: str, repo: str, pull_number: int, developer_login: str, conn: AsyncpgConnection, action: str, log: Any = None) -> None:
    if log is None:
        import structlog
        log = structlog.get_logger(__name__)
        
    team_id, repo_id = await get_or_create_team_and_repo(conn, owner, repo)
    team_rules = await get_active_rules(conn, team_id)

    pull_response = await installation_client.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
    pull_response.raise_for_status()
    head_sha = pull_response.json()["head"]["sha"]

    changed = None
    is_incremental = False
    
    if action == "synchronize":
        last_sha_row = await conn.fetchrow("SELECT last_reviewed_sha FROM pr_state WHERE repo_id = $1 AND pull_number = $2", repo_id, pull_number)
        if last_sha_row:
            last_sha = last_sha_row["last_reviewed_sha"]
            from .fetch_diff import fetch_files_since
            changed = await fetch_files_since(installation_client, owner, repo, last_sha, head_sha)
            if changed is not None:
                is_incremental = True
                
    if changed is None:
        from .fetch_diff import fetch_changed_files
        changed = await fetch_changed_files(installation_client, owner, repo, pull_number)

    issue_comment_url = f"/repos/{owner}/{repo}/issues/{pull_number}/comments"
    if changed["too_large"]:
        response = await installation_client.post(issue_comment_url, json={"body": f"DevBrief skipped this pull request because it has more than 40 changed files (at least {changed['file_count']})."})
        response.raise_for_status()
        return

    previous_unresolved_by_file: dict[str, list[dict[str, Any]]] = {}
    if is_incremental:
        filenames = [f.get("filename", "") for f in changed["reviewable_files"]]
        if filenames:
            rows = await conn.fetch("""
                SELECT i.id, i.file, i.category, i.severity, i.is_custom_rule_violation, i.matched_rule, i.issue, i.why, i.fix
                FROM review_issues i
                JOIN reviews r ON i.review_id = r.id
                WHERE r.repo_id = $1 AND r.pull_number = $2 AND i.resolved = false AND i.file = ANY($3)
            """, repo_id, pull_number, filenames)
            for row in rows:
                row_dict = dict(row)
                previous_unresolved_by_file.setdefault(row_dict["file"], []).append(row_dict)

    semaphore = asyncio.Semaphore(5)
    failed_files: list[dict[str, str]] = []

    async def review_file(changed_file: dict[str, Any]) -> tuple[dict[str, Any], Any | None]:
        try:
            async with semaphore:
                from app.core.injection_scan import scan_for_injection
                scan_for_injection(changed_file["patch"], changed_file["filename"], f"{owner}/{repo}", pull_number)
                
                import os
                agentic_enabled = os.getenv("AGENTIC_REVIEW_ENABLED", "false").lower() == "true"
                diff = changed_file["patch"]
                line_count = len(diff.splitlines())
                
                if agentic_enabled and line_count < 150:
                    log.info(f"Routing {changed_file['filename']} ({line_count} lines) to review_diff_agentic")
                    import time

                    from app.agent.review_with_tools import review_diff_agentic
                    from app.core.review import ReviewResult, TokenUsage
                    start = time.perf_counter()
                    review = await review_diff_agentic(diff, changed_file["filename"], team_rules, installation_client, owner, repo, head_sha)
                    latency = (time.perf_counter() - start) * 1000
                    # Wrap the agentic review in a ReviewResult to match expected return type
                    result = ReviewResult(review=review, usage=TokenUsage(None, None, None), latency_ms=latency, attempts=1)
                else:
                    log.info(f"Routing {changed_file['filename']} ({line_count} lines) to review_diff")
                    result = await review_diff(diff, changed_file["filename"], team_rules)
                    
                return changed_file, result
        except Exception as error:
            failed_files.append({"file": changed_file.get("filename", "unknown"), "reason": str(error)})
            return changed_file, None

    reviewed_files = await asyncio.gather(*(review_file(changed_file) for changed_file in changed["reviewable_files"]))
    
    inline_comments: list[dict[str, Any]] = []
    fallback_notes: list[str] = []
    issue_count = 0
    db_issues = []
    resolved_issue_ids = []
    fixed_count = 0
    still_present_issues = []
    new_count = 0
    
    from .resolution import diff_against_previous
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_estimated_cost = 0.0
    
    for changed_file, result in reviewed_files:
        if result is None:
            continue
            
        if result.usage:
            in_t = result.usage.input_tokens or 0
            out_t = result.usage.output_tokens or 0
            total_prompt_tokens += in_t
            total_completion_tokens += out_t
            total_estimated_cost += (in_t / 1_000_000 * 0.15) + (out_t / 1_000_000 * 0.60)
            
        valid_lines = build_line_map(changed_file["patch"])
        filename = changed_file["filename"]
        new_issues = result.review.issues
        
        if is_incremental:
            prev_unresolved = previous_unresolved_by_file.get(filename, [])
            diff_result = await diff_against_previous(filename, new_issues, prev_unresolved)
            
            for ri in diff_result["resolved"]:
                resolved_issue_ids.append(ri["id"])
                fixed_count += 1
                
            for ri in diff_result["still_present"]:
                still_present_issues.append(ri)
                
            issues_to_insert = diff_result["new"]
            new_count += len(issues_to_insert)
        else:
            issues_to_insert = new_issues

        for issue in issues_to_insert:
            issue_count += 1
            db_issues.append((
                issue.file,
                issue.category,
                issue.severity,
                issue.is_custom_rule_violation,
                issue.matched_rule,
                issue.issue,
                issue.why,
                issue.fix,
            ))
            line = find_nearest_valid_line(issue.start_line, valid_lines)
            if line is None:
                fallback_notes.append(f"`{issue.file}` line {issue.start_line}: {issue.issue}")
                continue
            inline_comments.append({"path": filename, "line": line, "side": "RIGHT", "body": _comment_body(issue)})

    if is_incremental:
        summary_body = _incremental_summary(fixed_count, still_present_issues, new_count, len(changed["skipped_files"]), failed_files, fallback_notes)
    else:
        summary_body = _summary(issue_count, len(changed["skipped_files"]), failed_files, fallback_notes)

    response = await installation_client.post(
        f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        json={
            "commit_id": head_sha,
            "event": "COMMENT",
            "body": summary_body,
            "comments": inline_comments,
        },
    )
    response.raise_for_status()

    await conn.execute("BEGIN")
    try:
        review_id = await conn.fetchval(
            "INSERT INTO reviews (team_id, repo_id, pull_number, developer_login, head_sha, prompt_tokens, completion_tokens, estimated_cost_usd) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id",
            team_id, repo_id, pull_number, developer_login, head_sha, total_prompt_tokens, total_completion_tokens, total_estimated_cost
        )
        for dbi in db_issues:
            await conn.execute(
                "INSERT INTO review_issues (review_id, file, category, severity, is_custom_rule_violation, matched_rule, issue, why, fix) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                review_id, *dbi
            )
            
        if resolved_issue_ids:
            await conn.execute("UPDATE review_issues SET resolved = true WHERE id = ANY($1)", resolved_issue_ids)
            
        await conn.execute(
            "INSERT INTO pr_state (repo_id, pull_number, last_reviewed_sha) VALUES ($1, $2, $3) ON CONFLICT (repo_id, pull_number) DO UPDATE SET last_reviewed_sha = $3",
            repo_id, pull_number, head_sha
        )
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        raise
