"""Prints review metrics: average latency, average cost per review, failure rate.

Run from the repo root (the AI engine does not need to be running):

    .venv\\Scripts\\python.exe services\\ai-engine\\scripts\\metrics_report.py
    .venv\\Scripts\\python.exe services\\ai-engine\\scripts\\metrics_report.py --days 7

Reads the `review_metrics` table written by app/metrics.py, using DATABASE_URL
from the repo's .env.
"""

import argparse
import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()


def fmt_cost(value) -> str:
    return "n/a" if value is None else f"${float(value):.6f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize DevBrief review metrics.")
    parser.add_argument("--days", type=int, default=None, help="only include the last N days")
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set. Run setup.ps1 first.", file=sys.stderr)
        return 1

    where = "WHERE created_at >= now() - make_interval(days => %s)" if args.days else ""
    params = (args.days,) if args.days else ()

    summary_sql = f"""
        SELECT
            count(*)                                              AS reviews,
            count(*) FILTER (WHERE NOT success)                   AS failures,
            avg(latency_ms)                                       AS avg_latency,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency,
            avg(cost_usd)                                         AS avg_cost,
            sum(cost_usd)                                         AS total_cost,
            count(*) FILTER (WHERE cost_usd IS NULL)              AS unpriced,
            avg(input_tokens)                                     AS avg_in,
            avg(output_tokens)                                    AS avg_out,
            count(*) FILTER (WHERE attempts > 1)                  AS retried,
            avg(attempts)                                         AS avg_attempts
        FROM review_metrics {where}
    """
    by_model_sql = f"""
        SELECT provider, model, count(*),
               count(*) FILTER (WHERE NOT success),
               avg(latency_ms), avg(cost_usd)
        FROM review_metrics {where}
        GROUP BY provider, model
        ORDER BY count(*) DESC
    """
    errors_sql = f"""
        SELECT error_type, count(*) FROM review_metrics
        {where + " AND" if where else "WHERE"} NOT success
        GROUP BY error_type ORDER BY count(*) DESC
    """

    try:
        with psycopg.connect(url) as conn, conn.cursor() as cur:
            cur.execute(summary_sql, params)
            row = cur.fetchone()
            cur.execute(by_model_sql, params)
            models = cur.fetchall()
            cur.execute(errors_sql, params)
            errors = cur.fetchall()
    except psycopg.errors.UndefinedTable:
        print("The review_metrics table does not exist yet. Run: .\\setup.ps1", file=sys.stderr)
        return 1

    (reviews, failures, avg_latency, p95, avg_cost, total_cost, unpriced,
     avg_in, avg_out, retried, avg_attempts) = row
    scope = f"last {args.days} day(s)" if args.days else "all time"
    print(f"DevBrief review metrics ({scope})")
    print("-" * 52)
    if not reviews:
        print("No reviews recorded yet. Run a review, then try again.")
        return 0

    print(f"Reviews recorded      : {reviews}")
    print(f"Failure rate          : {failures / reviews:.1%}  ({failures} of {reviews})")
    print(
        f"Needed retries        : {retried / reviews:.1%}  ({retried} of {reviews}; "
        f"{avg_attempts:.2f} model calls per review on average)"
    )
    print(f"Average latency       : {avg_latency:,.0f} ms   (p95 {p95:,.0f} ms)")
    print(f"Average cost / review : {fmt_cost(avg_cost)}   (estimated at list price)")
    print(f"Total estimated cost  : {fmt_cost(total_cost)}")
    if unpriced:
        print(f"  note: {unpriced} review(s) had no cost (unknown model price or no token usage);")
        print("        they are left out of the cost average.")
    if avg_in is not None:
        print(f"Average tokens        : {avg_in:,.0f} in / {avg_out:,.0f} out")

    print()
    print(f"{'provider':<11}{'model':<30}{'reviews':>8}{'failed':>8}{'avg ms':>9}{'avg cost':>14}")
    for provider, model, n, failed, avg_ms, cost in models:
        print(f"{provider:<11}{model:<30}{n:>8}{failed:>8}{avg_ms:>9,.0f}{fmt_cost(cost):>14}")

    if errors:
        print()
        print("Failures by type:")
        for error_type, n in errors:
            print(f"  {error_type}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
