"""Answer a question from the stored documents, with numbered citations.

Used by the "Ask your documents" page. Repeated questions reuse the saved answer.
Run on its own from the project folder:
    python -m core.ask "your question here"
"""
import hashlib
import re
import sys
import time

from core.db import bump_corpus_version, fetch_all, get_connection
from core.generate import generate_text
from core.retrieve import retrieve
from core.stats import current_corpus_version, get_chunks_by_ids

CACHE_DAYS = 7  # saved answers are reused for this many days
NOT_FOUND = "I don't know from the provided sources."


def normalize_question(question: str) -> str:
    # Lowercase and squeeze spaces, so "What  is X?" and "what is x?" count as the same question.
    return re.sub(r"\s+", " ", question.strip().lower())


def question_key(question: str) -> str:
    # A short fingerprint of the question, used to find its saved answer.
    return hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()


def cited_numbers(answer: str) -> set[int]:
    """Which sources the answer mentions, like [1] or [3]."""
    numbers = set()
    for number_text in re.findall(r"\[(\d+)\]", answer):
        numbers.add(int(number_text))
    return numbers


def build_prompt(question: str, chunks: list[dict]) -> str:
    # Number each passage so Gemini can cite it as [1], [2], and so on.
    lines = []
    number = 1
    for chunk in chunks:
        lines.append(f"[{number}] {chunk['text']}")
        number += 1
    sources = "\n".join(lines)

    return (
        "You answer questions using ONLY the numbered sources below.\n"
        "Cite the sources you used, like [1]. "
        f"If the sources do not contain the answer, reply exactly: {NOT_FOUND}\n\n"
        f"Sources:\n{sources}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def clear_answer_cache() -> None:
    # Makes every saved answer out of date. The question history is kept.
    with get_connection() as conn:
        bump_corpus_version(conn)


def get_cached(key: str, version: int):
    """Return the saved answer for this question, or None if there is none."""
    rows = fetch_all(
        """
        select answer, chunk_ids, model from query_traces
        where question_key = %s
          and corpus_version = %s
          and created_at > now() - make_interval(days => %s)
        order by created_at desc
        limit 1
        """,
        (key, version, CACHE_DAYS),
    )
    if not rows:
        return None
    answer, chunk_ids, model = rows[0]
    return {"answer": answer, "chunk_ids": list(chunk_ids or []), "model": model, "cached": True}


def save_trace(question, key, version, answer, chunk_ids, model, latency_ms) -> None:
    # Save the question and answer, so a repeat question can reuse it.
    with get_connection() as conn:
        conn.execute(
            """
            insert into query_traces
                (question, answer, chunk_ids, provider, model, latency_ms, question_key, corpus_version)
            values (%s, %s, %s, 'gemini', %s, %s, %s, %s)
            """,
            (question, answer, chunk_ids, model, latency_ms, key, version),
        )


def ask(question: str) -> dict:
    """Return {"answer", "chunks", "cached", "model"}. Saved and new answers look the same."""
    key = question_key(question)
    version = current_corpus_version()

    # 1. Reuse the saved answer if nothing changed since it was written.
    cached = get_cached(key, version)
    if cached:
        chunks = get_chunks_by_ids(cached["chunk_ids"])
        # If a cited passage was deleted, the [1], [2] numbers would point at the
        # wrong passages. Then skip the saved answer and write a new one.
        if len(chunks) == len(cached["chunk_ids"]):
            return {"answer": cached["answer"], "chunks": chunks, "cached": True, "model": cached["model"]}

    # 2. Find related passages. retrieve() already drops the weak matches.
    chunks = retrieve(question)
    if not chunks:
        # Nothing related: no need to ask Gemini, and nothing to save.
        return {"answer": NOT_FOUND, "chunks": [], "cached": False, "model": None}

    # 3. Ask Gemini and measure how long it took. If it fails, nothing is saved.
    start = time.perf_counter()
    answer, model = generate_text(build_prompt(question, chunks))
    latency_ms = int((time.perf_counter() - start) * 1000)

    # 4. Save the answer for next time.
    chunk_ids = []
    for chunk in chunks:
        chunk_ids.append(int(chunk["chunk_id"]))
    save_trace(question, key, version, answer, chunk_ids, model, latency_ms)
    return {"answer": answer, "chunks": chunks, "cached": False, "model": model}


def main() -> None:
    if len(sys.argv) < 2:
        print('usage: python -m core.ask "your question"')
        return

    result = ask(" ".join(sys.argv[1:]))
    print(result["answer"])
    print("(saved answer)" if result["cached"] else "(new answer)")
    number = 1
    for chunk in result["chunks"]:
        print(f"[{number}] {chunk['filename']} passage {chunk['chunk_id']}")
        number += 1


if __name__ == "__main__":
    main()
