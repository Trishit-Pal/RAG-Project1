"""Give every file a quality score from 0 (bad) to 1 (perfect).

The score has three parts. The weights below are a design choice, not a standard.
Used by core/ingest.py; shown on the Data quality page.
"""
import json

import pandas as pd

# How much each part counts. They add up to 1.0.
WEIGHTS = {"completeness": 0.5, "uniqueness": 0.3, "validity": 0.2}


def combine_scores(completeness: float, uniqueness: float, passed: bool, rows_in: int) -> dict:
    # validity is 1 if the file passed the upload checks, otherwise 0.
    validity = 1.0 if passed else 0.0
    details = {"completeness": completeness, "uniqueness": uniqueness, "validity": validity}

    total = 0.0
    for name, weight in WEIGHTS.items():
        total += weight * details[name]

    return {
        "score": round(total, 4),
        "details": details,
        # The database needs these two counts. A file that failed passes none of its rows.
        "rows_in": rows_in,
        "rows_passed": rows_in if passed else 0,
    }


def score_table(df: pd.DataFrame, passed: bool) -> dict:
    if df.empty:
        return combine_scores(0.0, 0.0, passed, rows_in=0)
    # Share of cells that are NOT empty.
    completeness = float(1 - df.isna().to_numpy().mean())
    # Share of rows that are NOT repeats of an earlier row.
    uniqueness = float(1 - df.duplicated().sum() / len(df))
    return combine_scores(completeness, uniqueness, passed, rows_in=len(df))


def score_pages(pages: list[str], passed: bool) -> dict:
    if not pages:
        return combine_scores(0.0, 0.0, passed, rows_in=0)

    pages_with_text = 0
    for page in pages:
        if page.strip():
            pages_with_text += 1
    completeness = pages_with_text / len(pages)
    # set() keeps one copy of each different page, so repeats lower this number.
    uniqueness = len(set(pages)) / len(pages)
    return combine_scores(completeness, uniqueness, passed, rows_in=len(pages))


def insert_quality_run(conn, source_id, result: dict) -> None:
    # conn is an open database connection. The caller decides when to save.
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
    conn.execute("update sources set quality_score = %s where id = %s", (result["score"], source_id))
