from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from devbrief_core.schema import IssueCategory, Severity


class ExpectedIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: IssueCategory
    description: str
    must_mention: list[str] = Field(alias="mustMention")
    severity: Severity


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_pr: HttpUrl | None = Field(default=None, alias="sourcePr")
    language: str
    diff: str
    expected_issues: list[ExpectedIssue] = Field(alias="expectedIssues")
    notes_for_labeler: str | None = Field(default=None, alias="notesForLabeler")

