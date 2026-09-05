from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

IssueCategory = Literal["single-responsibility", "naming", "error-handling", "security", "duplication", "complexity", "style", "other"]
Severity = Literal["low", "medium", "high"]


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    start_line: int = Field(alias="startLine")
    end_line: int | None = Field(default=None, alias="endLine")
    category: IssueCategory
    severity: Severity
    issue: str
    why: str
    fix: str
    learn_more_url: HttpUrl | None = Field(default=None, alias="learnMoreUrl")
    is_custom_rule_violation: bool = Field(default=False, alias="isCustomRuleViolation")


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[Issue]


def _require_all_object_properties(value: object) -> object:
    if isinstance(value, list):
        return [_require_all_object_properties(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _require_all_object_properties(child) for key, child in value.items()}
    properties = result.get("properties")
    if isinstance(properties, dict):
        result["required"] = list(properties.keys())
    return result


def groq_strict_json_schema(model: type[BaseModel]) -> dict[str, object]:
    """Convert a Pydantic schema for Groq strict structured output.

    Groq requires every declared object property to appear in `required`.
    Optional fields are nullable in Pydantic's JSON schema and remain optional
    in the parsed Python model.
    """
    return _require_all_object_properties(model.model_json_schema())  # type: ignore[return-value]


REVIEW_JSON_SCHEMA = groq_strict_json_schema(Review)

