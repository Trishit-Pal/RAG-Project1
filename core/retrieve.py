"""Search: find the stored passages most similar to a question.

Used by core/ask.py (to answer) and core/evals.py (to test search).
The search itself runs in the database: see match_chunks() in sql/002_match_chunks.sql.
"""
from core.db import fetch_all, rows_to_dicts, to_vector_text
from core.embed import embed_texts

TOP_K = 6              # how many passages to return at most
MIN_SIMILARITY = 0.3   # passages less similar than this are treated as unrelated (a judgment call)


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    """Return up to k passages, most similar first, each with its file name and source."""
    # 1. Turn the question into a vector.
    question_vector = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]

    # 2. Ask the database for the k closest passages, with each one's file name and source.
    # The last argument (0) means "keep every source, whatever its quality score".
    # The ::int and ::real casts are needed: without them Postgres looks for
    # match_chunks(vector, smallint, double precision), which does not exist.
    rows = fetch_all(
        """
        select m.chunk_id, m.document_id, m.text, m.similarity, d.filename, d.source_id
        from match_chunks(%s::vector, %s::int, 0::real) m
        join documents d on d.id = m.document_id
        order by m.similarity desc
        """,
        (to_vector_text(question_vector), k),
    )
    names = ["chunk_id", "document_id", "text", "similarity", "filename", "source_id"]

    # 3. Keep only the passages that are close enough.
    chunks = []
    for chunk in rows_to_dicts(names, rows):
        chunk["similarity"] = float(chunk["similarity"])
        if chunk["similarity"] >= MIN_SIMILARITY:
            chunks.append(chunk)
    return chunks
