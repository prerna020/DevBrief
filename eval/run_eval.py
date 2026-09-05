from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from devbrief_core.review import ReviewError, review_diff
from .judge import judge_review
from .load_golden import load_golden_cases

INPUT_COST_PER_MILLION = 0.15
OUTPUT_COST_PER_MILLION = 0.60
REPORT_DIRECTORY = Path(__file__).parent / "report"


async def main(prompt_version: str) -> None:
    golden_cases = load_golden_cases()
    results = []
    for golden in golden_cases:
        try:
            review = await review_diff(golden.diff, golden.id)
            judgement = await judge_review(golden.expected_issues, review.review.issues)
            results.append({"id": golden.id, "review": review, "judgement": judgement, "error": None, "attempts": review.attempts})
        except Exception as error:
            results.append({"id": golden.id, "review": None, "judgement": None, "error": str(error), "attempts": error.attempts if isinstance(error, ReviewError) else 1})
    successful = [result for result in results if result["review"] is not None]
    total_expected = sum(len(case.expected_issues) for case in golden_cases)
    matched = sum(sum(match.matched for match in result["judgement"].matches) for result in successful)
    attempts = sum(result["attempts"] for result in results)
    input_tokens = sum(result["review"].usage.input_tokens or 0 for result in successful)
    output_tokens = sum(result["review"].usage.output_tokens or 0 for result in successful)
    now = datetime.now(timezone.utc)
    summary = {
        "date": now.isoformat(), "promptVersion": prompt_version, "caseCount": len(golden_cases),
        "recall": 1 if total_expected == 0 else matched / total_expected,
        "schemaValidityRate": 1 if attempts == 0 else len(successful) / attempts,
        "avgLatencyMs": 0 if not successful else sum(result["review"].latency_ms for result in successful) / len(successful),
        "avgInputTokens": 0 if not successful else input_tokens / len(successful),
        "avgOutputTokens": 0 if not successful else output_tokens / len(successful),
        "estimatedCostUsd": input_tokens / 1_000_000 * INPUT_COST_PER_MILLION + output_tokens / 1_000_000 * OUTPUT_COST_PER_MILLION,
    }
    unmatched = [{"caseId": result["id"], **item.model_dump(by_alias=True, mode="json")} for result in successful for item in result["judgement"].unmatched]
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (REPORT_DIRECTORY / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json").write_text(json.dumps({"summary": summary, "cases": results, "unmatched": unmatched}, default=lambda value: value.model_dump(by_alias=True, mode="json"), indent=2), encoding="utf-8")
    with (REPORT_DIRECTORY / "HISTORY.md").open("a", encoding="utf-8") as history:
        history.write(f"{summary['date']} | prompt={prompt_version} | recall={summary['recall']:.3f} | schemaValidityRate={summary['schemaValidityRate']:.3f} | cases={summary['caseCount']}\n")
    print("\nDevBrief evaluation summary")
    for key, value in summary.items(): print(f"  {key}: {value}")
    print(f"  unmatched actual issues: {len(unmatched)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", default="v1")
    asyncio.run(main(parser.parse_args().prompt_version))

