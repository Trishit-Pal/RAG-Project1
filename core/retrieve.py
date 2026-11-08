"""Search: find the stored passages most similar to a question.

Used by core/ask.py (to answer) and core/evals.py (to test search).
The search itself runs in the database: see match_chunks() in sql/002_match_chunks.sql.
"""
from core.db import fetch_all, to_vector_text
from core.embed import embed_texts

# Passages less similar than this are treated as unrelated (a judgment call).
MIN_SIMILARITY = 0.3


def retrieve(question: str, k: int = 6, min_quality: float = 0.0,
             min_similarity: float = MIN_SIMILARITY) -> list[dict]:
    """Return up to k passages, most similar first, each with its file name.

    k: how many passages to return at most.
    min_quality: skip sources whose quality score is lower than this.
    min_similarity: skip passages less similar than this.
    """
    # 1. Turn the question into a vector.
    question_vector = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]

    # 2. Ask the database for the k closest passages, plus each one's file name.
    # The ::int and ::real casts are needed: without them Postgres looks for
    # match_chunks(vector, smallint, double precision), which does not exist.
    rows = fetch_all(
        """
        select m.chunk_id, m.document_id, m.text, m.similarity, m.source_quality, d.filename
        from match_chunks(%s::vector, %s::int, %s::real) m
        join documents d on d.id = m.document_id
        order by m.similarity desc
        """,
        (to_vector_text(question_vector), k, min_quality),
    )

    # 3. Keep only close enough passages, as dictionaries that are easy to read.
    chunks = []
    for row in rows:
        similarity = float(row[3])
        if similarity < min_similarity:
            continue
        chunks.append({
            "chunk_id": row[0],
            "document_id": row[1],
            "text": row[2],
            "similarity": similarity,
            "source_quality": float(row[4] or 0),  # "or 0": a missing score counts as 0
            "filename": row[5],
        })
    return chunks
