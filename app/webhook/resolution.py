from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.groq_client import create_groq_client
from app.core.schema import Issue, groq_strict_json_schema

RETRY_DELAYS_SECONDS = (0.5, 1.5, 4.0)

def _is_retriable(error: Exception) -> bool:
    return isinstance(error, (json.JSONDecodeError, ValidationError, ConnectionError, TimeoutError, OSError))

class ResolutionMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matched: bool
    matched_new_issue_index: int | None = Field(alias="matchedNewIssueIndex")

class ResolutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matches: list[ResolutionMatch]

async def diff_against_previous(file: str, new_issues: list[Issue], previous_unresolved_issues_for_file: list[dict[str, Any]]) -> dict[str, list[Any]]:
    if not previous_unresolved_issues_for_file:
        return {"resolved": [], "still_present": [], "new": new_issues}
    if not new_issues:
        return {"resolved": previous_unresolved_issues_for_file, "still_present": [], "new": []}

    client = create_groq_client()
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    expected_issues = [{"issue": p["issue"], "why": p["why"], "fix": p["fix"]} for p in previous_unresolved_issues_for_file]
    actual_issues = [item.model_dump(by_alias=True, mode="json") for item in new_issues]
    
    for attempt, delay in enumerate(RETRY_DELAYS_SECONDS, start=1):
        try:
            completion = await client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_schema", "json_schema": {"name": "resolution_result", "strict": True, "schema": groq_strict_json_schema(ResolutionResponse)}},
                messages=[
                    {"role": "system", "content": "Compare previous unresolved issues and new issues on a file. For each previous issue, decide if any new issue substantively matches it; exact wording is not required. Return one matches entry per previous issue. Use the new issue index if matched, otherwise null. Return only schema-conforming JSON."},
                    {"role": "user", "content": json.dumps({"previousIssues": expected_issues, "newIssues": actual_issues})},
                ],
            )
            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                raise ValueError("Groq returned an empty response.")
            parsed = ResolutionResponse.model_validate(json.loads(content))
            
            resolved = []
            still_present = []
            matched_new_indices = set()
            
            for i, match in enumerate(parsed.matches):
                if match.matched and match.matched_new_issue_index is not None:
                    still_present.append(previous_unresolved_issues_for_file[i])
                    matched_new_indices.add(match.matched_new_issue_index)
                else:
                    resolved.append(previous_unresolved_issues_for_file[i])
                    
            new = [issue for i, issue in enumerate(new_issues) if i not in matched_new_indices]
            return {"resolved": resolved, "still_present": still_present, "new": new}
            
        except Exception as error:
            if not _is_retriable(error) or attempt == len(RETRY_DELAYS_SECONDS):
                return {"resolved": [], "still_present": previous_unresolved_issues_for_file, "new": new_issues}
            await asyncio.sleep(delay)
            
    return {"resolved": [], "still_present": previous_unresolved_issues_for_file, "new": new_issues}
