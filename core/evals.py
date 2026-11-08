"""Retrieval evaluation: does a saved question find the source we expect?

Each saved test case has a question and the sources that should answer it.
A case is a "hit" if any of the retrieved chunks comes from one of those sources.
This checks retrieval only, so it does not call the answer model (saves quota).
"""
import json
import subprocess

from core.db import fetch_all, get_connection, rows_to_dicts
from core.retrieve import retrieve

PASS_HIT_RATE = 0.7  # the run passes at 70% hits or more (judgment, easy to change)
TOP_K = 6


# ---------- pure helpers (no database, easy to test) ----------

def is_hit(expected_source_ids: list, retrieved_source_ids: list) -> bool:
    # A hit when the two lists share at least one source.
    return bool(set(expected_source_ids) & set(retrieved_source_ids))


def summarize(hits: list[bool]) -> tuple[dict, bool]:
    total = len(hits)
    count = sum(hits)
    hit_rate = round(count / total, 4) if total else 0.0
    metrics = {"cases": total, "hits": count, "hit_rate": hit_rate}
    return metrics, total > 0 and hit_rate >= PASS_HIT_RATE


# ---------- database ----------

def add_case(question: str, expected_source_ids: list, reference_answer: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "insert into eval_cases (question, expected_source_ids, reference_answer) "
            "values (%s, %s, %s)",
            (question.strip(), expected_source_ids, reference_answer),
        )


def list_cases() -> list[dict]:
    rows = fetch_all(
        "select id, question, expected_source_ids, reference_answer from eval_cases order by id"
    )
    return [
        {"id": r[0], "question": r[1], "expected_source_ids": list(r[2]), "reference_answer": r[3]}
        for r in rows
    ]


def delete_case(case_id: int) -> None:
    with get_connection() as conn:
        conn.execute("delete from eval_cases where id = %s", (case_id,))


def list_runs(limit: int = 20) -> list[dict]:
    rows = fetch_all(
        "select run_at, git_sha, metrics, passed from eval_runs order by run_at desc limit %s",
        (limit,),
    )
    return rows_to_dicts(["run_at", "git_sha", "metrics", "passed"], rows)


def source_of_documents(document_ids: list) -> dict:
    # {document id: source id}, for all documents in one query.
    if not document_ids:
        return {}
    rows = fetch_all("select id, source_id from documents where id = any(%s)", (document_ids,))
    return dict(rows)


def _git_sha() -> str:
    # Records which version of the code produced the result.
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def save_run(metrics: dict, passed: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "insert into eval_runs (git_sha, metrics, passed) values (%s, %s::jsonb, %s)",
            (_git_sha(), json.dumps(metrics), passed),
        )


# ---------- the run ----------

def run_eval() -> dict:
    """Run every saved case. Returns {"results": [...], "metrics": {...}, "passed": bool}."""
    cases = list_cases()
    # 1. Search for every question. retrieve() uses the same cut-off as ask(),
    #    so this measures what answers really use.
    found = {case["id"]: [c["document_id"] for c in retrieve(case["question"], TOP_K)] for case in cases}

    # 2. Look up which source each document belongs to, in one query.
    all_documents = list({doc for docs in found.values() for doc in docs})
    source_of = source_of_documents(all_documents)

    # 3. Score each question.
    results = []
    for case in cases:
        found_sources = [source_of.get(doc) for doc in found[case["id"]]]
        results.append({
            "question": case["question"],
            "hit": is_hit(case["expected_source_ids"], found_sources),
        })

    metrics, passed = summarize([r["hit"] for r in results])
    if results:  # nothing to save for an empty test set
        save_run(metrics, passed)
    return {"results": results, "metrics": metrics, "passed": passed}
