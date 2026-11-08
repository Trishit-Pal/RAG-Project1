"""Phase 7a: find the chunks most similar to a question.

Uses the match_chunks() SQL function from sql/002_match_chunks.sql.
"""
from core.db import fetch_all
from core.embed import embed_texts
from core.vectors import to_vector_literal

# Chunks below this score are treated as unrelated (judgment). Filtering here
# means every caller (answers and evaluation) uses the same cut-off.
MIN_SIMILARITY = 0.3


def retrieve(
    question: str, k: int = 6, min_quality: float = 0.0, min_similarity: float = MIN_SIMILARITY
) -> list[dict]:
    # 1. Turn the question into a vector. Questions use the RETRIEVAL_QUERY task type.
    query_vec = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]

    # 2. Ask Postgres for the k closest chunks. The ::casts matter: without them
    # psycopg sends k as smallint and min_quality as double precision, and
    # Postgres reports that match_chunks(vector, smallint, double precision) does not exist.
    rows = fetch_all(
        "select chunk_id, document_id, text, similarity, source_quality "
        "from match_chunks(%s::vector, %s::int, %s::real)",
        (to_vector_literal(query_vec), k, min_quality),
    )

    # 3. Convert each row to a dictionary and drop the weak matches.
    chunks = [
        {
            "chunk_id": r[0],
            "document_id": r[1],
            "text": r[2],
            "similarity": float(r[3]),
            "source_quality": float(r[4] or 0),
        }
        for r in rows
    ]
    return [c for c in chunks if c["similarity"] >= min_similarity]
