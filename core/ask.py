"""Phase 7c: answer a question from the corpus, with citations and a cache.

Run from the project root:
    python -m core.ask "your question here"
"""
import hashlib
import re
import sys
import time

from core.db import fetch_all, get_connection
from core.generate import generate_text
from core.retrieve import retrieve
from core.stats import attach_filenames, get_chunks_by_ids

MIN_SIMILARITY = 0.3  # chunks below this score are treated as unrelated (judgment)
CACHE_DAYS = 7        # cached answers expire after this many days (judgment)
NOT_FOUND = "I don't know from the provided sources."


def normalize_question(question: str) -> str:
    # Lowercase and collapse spaces, so "What  is X?" and "what is x?" match.
    return re.sub(r"\s+", " ", question.strip().lower())


def question_key(question: str) -> str:
    return hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()


def current_corpus_version() -> int:
    rows = fetch_all("select corpus_version from corpus_state where id = 1")
    return int(rows[0][0])


def get_cached(key: str, version: int) -> dict | None:
    # A cached answer is only valid if the corpus has not changed since it was saved.
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


def build_prompt(question: str, chunks: list[dict]) -> str:
    # Number each source so the model can cite it as [1], [2], and so on.
    numbered = "\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks, start=1))
    return (
        "You answer questions using ONLY the numbered sources below.\n"
        "Cite the sources you used, like [1]. "
        f"If the sources do not contain the answer, reply exactly: {NOT_FOUND}\n\n"
        f"Sources:\n{numbered}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def save_trace(question, key, version, answer, chunk_ids, model, latency_ms) -> None:
    # provider is fixed to 'gemini'. model is whichever model actually answered.
    with get_connection() as conn:
        conn.execute(
            """
            insert into query_traces
                (question, answer, chunk_ids, provider, model, latency_ms,
                 question_key, corpus_version)
            values (%s, %s, %s, 'gemini', %s, %s, %s, %s)
            """,
            (question, answer, chunk_ids, model, latency_ms, key, version),
        )


def ask(question: str) -> dict:
    """Return {"answer", "chunks", "cached", "model"}. Fresh and cached answers have the same shape."""
    key = question_key(question)
    version = current_corpus_version()

    # 1. Return the saved answer if this question was already answered on this corpus.
    cached = get_cached(key, version)
    if cached:
        chunks = attach_filenames(get_chunks_by_ids(cached["chunk_ids"]))
        return {"answer": cached["answer"], "chunks": chunks, "cached": True, "model": cached["model"]}

    # 2. Find related chunks and drop the weak matches.
    chunks = [c for c in retrieve(question) if c["similarity"] >= MIN_SIMILARITY]
    if not chunks:
        # No LLM call, and nothing saved to the cache.
        return {"answer": NOT_FOUND, "chunks": [], "cached": False, "model": None}

    # 3. Ask Gemini and time the call. If it raises, nothing is saved.
    start = time.perf_counter()
    answer, model = generate_text(build_prompt(question, chunks))
    latency_ms = int((time.perf_counter() - start) * 1000)

    # 4. Save the successful answer for next time.
    chunk_ids = [int(c["chunk_id"]) for c in chunks]
    save_trace(question, key, version, answer, chunk_ids, model, latency_ms)
    return {"answer": answer, "chunks": attach_filenames(chunks), "cached": False, "model": model}


def main() -> None:
    if len(sys.argv) < 2:
        print('usage: python -m core.ask "your question"')
        return

    result = ask(" ".join(sys.argv[1:]))
    print(result["answer"])
    print("(from cache)" if result["cached"] else "(fresh answer)")
    for i, c in enumerate(result["chunks"], start=1):
        print(f"[{i}] {c['filename']} chunk {c['chunk_id']}")


if __name__ == "__main__":
    main()