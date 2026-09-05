from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .golden_schema import GoldenCase

GOLDEN_DIRECTORY = Path(__file__).parent / "golden"


def load_golden_cases(directory: Path = GOLDEN_DIRECTORY) -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            cases.append(GoldenCase.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise ValueError(f"Invalid golden case {path.name}: {error}") from error
    return cases

