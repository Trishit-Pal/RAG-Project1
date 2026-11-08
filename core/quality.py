"""Phase 6: data quality scores.

The three checks are documented data quality dimensions (completeness,
uniqueness, validity). The weights below are my design judgment, not a standard.
"""
import json

import pandas as pd

# Weights must add up to 1.0.
WEIGHTS = {"completeness": 0.5, "uniqueness": 0.3, "validity": 0.2}


def _combine(parts: dict, passed: bool, rows_in: int) -> dict:
    # validity is 1.0 if the file passed Phase 4 validation, otherwise 0.0
    scores = {**parts, "validity": 1.0 if passed else 0.0}
    total = sum(WEIGHTS[name] * scores[name] for name in WEIGHTS)
    return {
        "score": round(total, 4),
        "details": scores,
        # The database requires these two counts for every quality run.
        # A file that failed validation passes none of its rows.
        "rows_in": rows_in,
        "rows_passed": rows_in if passed else 0,
    }


def score_table(df: pd.DataFrame, passed: bool) -> dict:
    # Empty tables get zero for the row-based checks.
    if df.empty:
        parts = {"completeness": 0.0, "uniqueness": 0.0}
    else:
        parts = {
            # share of cells that are NOT empty
            "completeness": float(1 - df.isna().to_numpy().mean()),
            # share of rows that are NOT duplicates
            "uniqueness": float(1 - df.duplicated().sum() / len(df)),
        }
    return _combine(parts, passed, rows_in=len(df))


def score_pages(pages: list[str], passed: bool) -> dict:
    if not pages:
        parts = {"completeness": 0.0, "uniqueness": 0.0}
    else:
        parts = {
            # share of pages that contain some text
            "completeness": sum(1 for p in pages if p.strip()) / len(pages),
            # share of pages whose text is distinct
            "uniqueness": len(set(pages)) / len(pages),
        }
    return _combine(parts, passed, rows_in=len(pages))


def insert_quality_run(conn, source_id, result: dict) -> None:
    # conn is an open database connection from core.db (passed in, so the
    # caller controls the transaction).
    details = result["details"]
    conn.execute(
        "insert into quality_runs "
        "(source_id, rows_in, rows_passed, completeness, duplicate_rate, score, details) "
        "values (%s, %s, %s, %s, %s, %s, %s::jsonb)",
        (
            source_id,
            result["rows_in"],
            result["rows_passed"],
            details["completeness"],
            1 - details["uniqueness"],  # duplicate rate is the opposite of uniqueness
            result["score"],
            json.dumps(details),
        ),
    )
    # Keep the latest score on the source row for the dashboard.
    conn.execute(
        "update sources set quality_score = %s where id = %s",
        (result["score"], source_id),
    )
