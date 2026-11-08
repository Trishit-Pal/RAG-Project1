"""Test the search: does a saved question find the source we expect?

Each saved test case has a question and the sources that should answer it.
A case is a "hit" if any passage the search finds comes from one of those sources.
This tests search only, so it never asks Gemini to write an answer (saves quota).
Used by the Evaluation page.
"""
import json
import subprocess

from core.db import fetch_all, get_connection, rows_to_dicts
from core.retrieve import TOP_K, retrieve

PASS_HIT_RATE = 0.7  # a run passes at 70% hits or more (a judgment call)


# ---------- small calculations (no database, easy to test) ----------

def is_hit(expected_source_ids: list, found_source_ids: list) -> bool:
    # A hit when at least one expected source was found.
    for source_id in expected_source_ids:
        if source_id in found_source_ids:
            return True
    return False


def summarize(hits: list[bool]) -> tuple[dict, bool]:
    """Return (numbers for the run, whether it passed)."""
    total = len(hits)
    count = sum(hits)  # True counts as 1 and False as 0
    if total == 0:
        hit_rate = 0.0
    else:
        hit_rate = round(count / total, 4)
    metrics = {"cases": total, "hits": count, "hit_rate": hit_rate}
    passed = total > 0 and hit_rate >= PASS_HIT_RATE
    return metrics, passed


# ---------- database ----------

def add_case(question: str, expected_source_ids: list, reference_answer: str = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "insert into eval_cases (question, expected_source_ids, reference_answer) values (%s, %s, %s)",
            (question.strip(), expected_source_ids, reference_answer),
        )


def list_cases() -> list[dict]:
    rows = fetch_all("select id, question, expected_source_ids, reference_answer from eval_cases order by id")
    cases = rows_to_dicts(["id", "question", "expected_source_ids", "reference_answer"], rows)
    for case in cases:
        case["expected_source_ids"] = list(case["expected_source_ids"])
    return cases


def delete_case(case_id: int) -> None:
    with get_connection() as conn:
        conn.execute("delete from eval_cases where id = %s", (case_id,))


def list_runs(limit: int = 20) -> list[dict]:
    rows = fetch_all(
        "select run_at, git_sha, metrics, passed from eval_runs order by run_at desc limit %s",
        (limit,),
    )
    return rows_to_dicts(["run_at", "git_sha", "metrics", "passed"], rows)


def git_version() -> str:
    # The short git commit id, to record which version of the code was tested.
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def save_run(metrics: dict, passed: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "insert into eval_runs (git_sha, metrics, passed) values (%s, %s::jsonb, %s)",
            (git_version(), json.dumps(metrics), passed),
        )


# ---------- the test run ----------

def run_eval() -> dict:
    """Run every saved case. Returns {"results": [...], "metrics": {...}, "passed": True/False}."""
    results = []
    hits = []
    for case in list_cases():
        # Search for the question. retrieve() uses the same cut-off as answers do,
        # and tells us which source each passage came from.
        found_sources = []
        for chunk in retrieve(case["question"], TOP_K):
            found_sources.append(chunk["source_id"])
        hit = is_hit(case["expected_source_ids"], found_sources)
        results.append({"question": case["question"], "hit": hit})
        hits.append(hit)

    metrics, passed = summarize(hits)
    if results:  # an empty test set is not worth saving
        save_run(metrics, passed)
    return {"results": results, "metrics": metrics, "passed": passed}
