"""Phase 7a: find the chunks most similar to a question.

Uses the match_chunks() SQL function from sql/002_match_chunks.sql.
"""
from core.db import fetch_all
from core.embed import embed_texts
from core.vectors import to_vector_literal


def retrieve(question: str, k: int = 6, min_quality: float = 0.0) -> list[dict]:
    # 1. Turn the question into a vector. Questions use the RETRIEVAL_QUERY task type.
    query_vec = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]

    # 2. Ask Postgres for the k closest chunks. %s::vector casts the text to a vector.
    rows = fetch_all(
        "select chunk_id, document_id, text, similarity, source_quality "
        "from match_chunks(%s::vector, %s, %s)",
        (to_vector_literal(query_vec), k, min_quality),
    )

    # 3. Convert each row to a dictionary so the rest of the code is easier to read.
    return [
        {
            "chunk_id": r[0],
            "document_id": r[1],
            "text": r[2],
            "similarity": float(r[3]),
            "source_quality": float(r[4] or 0),
        }
        for r in rows
    ]