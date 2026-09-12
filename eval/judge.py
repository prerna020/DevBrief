from __future__ import annotations

import asyncio
import json
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.groq_client import create_groq_client
from app.core.schema import Issue, groq_strict_json_schema
from .golden_schema import ExpectedIssue

RETRY_DELAYS_SECONDS = (0.5, 1.5, 4.0)


class ExpectedMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matched: bool
    matched_issue_index: int | None = Field(alias="matchedIssueIndex")


class JudgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matches: list[ExpectedMatch]
    unmatched_actual_issue_indexes: list[int] = Field(alias="unmatchedActualIssueIndexes")


class UnmatchedIssue(BaseModel):
    label: Literal["unmatched"] = "unmatched"
    actual_issue_index: int
    issue: Issue


class JudgeResult(BaseModel):
    matches: list[ExpectedMatch]
    unmatched: list[UnmatchedIssue]


class JudgeError(RuntimeError):
    def __init__(self, message: str, last_error: Exception | None) -> None:
        super().__init__(message)
        self.last_error = last_error


def _is_retriable(error: Exception) -> bool:
    return isinstance(error, (json.JSONDecodeError, ValidationError, ConnectionError, TimeoutError, OSError))


async def judge_review(expected_issues: list[ExpectedIssue], actual_issues: list[Issue]) -> JudgeResult:
    client = create_groq_client()
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS_SECONDS, start=1):
        try:
            completion = await client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_schema", "json_schema": {"name": "judge_result", "strict": True, "schema": groq_strict_json_schema(JudgeResponse)}},
                messages=[
                    {"role": "system", "content": "Compare expected and actual code-review issues semantically. For each expected issue, decide if any actual issue substantively matches the underlying problem; exact wording is not required. Return one matches entry per expected issue. Use the actual issue index if matched, otherwise null. Return all actual issue indexes that match no expected issue as unmatchedActualIssueIndexes. Call them unmatched, never false positives, because they could be valid additional issues. Return only schema-conforming JSON."},
                    {"role": "user", "content": json.dumps({"expectedIssues": [item.model_dump(by_alias=True, mode="json") for item in expected_issues], "actualIssues": [item.model_dump(by_alias=True, mode="json") for item in actual_issues]})},
                ],
            )
            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                raise ValueError("Groq returned an empty judge response.")
            parsed = JudgeResponse.model_validate(json.loads(content))
            if len(parsed.matches) != len(expected_issues):
                raise ValueError("Judge did not return one match for every expected issue.")
            indexes = {match.matched_issue_index for match in parsed.matches if match.matched_issue_index is not None}
            unmatched_indexes = set(parsed.unmatched_actual_issue_indexes)
            if any(index < 0 or index >= len(actual_issues) for index in indexes | unmatched_indexes):
                raise ValueError("Judge returned an out-of-range actual issue index.")
            return JudgeResult(matches=parsed.matches, unmatched=[UnmatchedIssue(actual_issue_index=index, issue=actual_issues[index]) for index in sorted(unmatched_indexes)])
        except Exception as error:
            last_error = error
            if not _is_retriable(error) or attempt == len(RETRY_DELAYS_SECONDS):
                break
            await asyncio.sleep(delay)
    raise JudgeError("Unable to generate a valid judgement after 3 attempts.", last_error)
