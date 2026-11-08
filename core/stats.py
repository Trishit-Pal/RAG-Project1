"""Read-only questions to the database, for the Streamlit pages.

Nothing here changes data. Each function returns plain lists and dictionaries.
"""
from core.db import fetch_all, rows_to_dicts


def current_corpus_version() -> int:
    # Goes up by 1 when documents are added or saved answers are cleared.
    # Saved answers are only reused while it stays the same.
    rows = fetch_all("select corpus_version from corpus_state where id = 1")
    return int(rows[0][0])


def count_indexed_documents() -> int:
    rows = fetch_all("select count(*) from documents where status = 'indexed'")
    return rows[0][0]


def overview() -> dict:
    """The numbers shown on the Home page."""
    # Rows like ("indexed", 4), ("quarantined", 1). dict() turns them into {"indexed": 4, ...}.
    status_rows = fetch_all("select status::text, count(*) from documents group by status")
    # Two counts in one query, because each query is a trip to the database.
    counts = fetch_all("select (select count(*) from chunks), (select count(*) from query_traces)")
    return {
        "documents": dict(status_rows),
        "chunks": counts[0][0],
        "questions": counts[0][1],
    }


def list_documents(limit: int = 200) -> list[dict]:
    rows = fetch_all(
        """
        select d.filename, s.name, d.status::text, d.byte_size, d.ingested_at,
               (select count(*) from chunks c where c.document_id = d.id)
        from documents d
        join sources s on s.id = d.source_id
        order by d.ingested_at desc
        limit %s
        """,
        (limit,),
    )
    return rows_to_dicts(["filename", "source", "status", "size_bytes", "ingested_at", "chunks"], rows)


def list_sources() -> list[dict]:
    rows = fetch_all("select id, name, kind::text, quality_score from sources order by name")
    return rows_to_dicts(["id", "name", "kind", "quality_score"], rows)


def list_quarantine(limit: int = 200) -> list[dict]:
    rows = fetch_all(
        """
        select d.filename, q.rule, q.reason, q.created_at
        from quarantine q
        join documents d on d.id = q.document_id
        order by q.created_at desc
        limit %s
        """,
        (limit,),
    )
    return rows_to_dicts(["filename", "rule", "reason", "created_at"], rows)


def list_quality_runs(limit: int = 100) -> list[dict]:
    rows = fetch_all(
        """
        select s.name, r.run_at, r.rows_in, r.rows_passed, r.completeness, r.duplicate_rate, r.score
        from quality_runs r
        join sources s on s.id = r.source_id
        order by r.run_at desc
        limit %s
        """,
        (limit,),
    )
    names = ["source", "run_at", "rows_in", "rows_passed", "completeness", "duplicate_rate", "score"]
    return rows_to_dicts(names, rows)


def recent_questions(limit: int = 10) -> list[dict]:
    rows = fetch_all(
        """
        select question, answer, model, latency_ms, created_at
        from query_traces
        order by created_at desc
        limit %s
        """,
        (limit,),
    )
    return rows_to_dicts(["question", "answer", "model", "latency_ms", "created_at"], rows)


def get_chunks_by_ids(chunk_ids: list[int]) -> list[dict]:
    """Load saved passages by id, in the same order as chunk_ids.

    Used for saved answers, which only remember which passages they used.
    """
    if not chunk_ids:
        return []
    rows = fetch_all(
        """
        select c.id, c.document_id, c.text, d.filename
        from chunks c
        join documents d on d.id = c.document_id
        where c.id = any(%s)
        """,
        (chunk_ids,),
    )

    # The database may return rows in any order, so look each one up by id.
    found = {}
    for row in rows:
        found[row[0]] = {
            "chunk_id": row[0],
            "document_id": row[1],
            "text": row[2],
            "filename": row[3],
            "similarity": None,  # not saved with the answer
        }

    # Keep the original order, so the [1], [2] numbers in the answer still match.
    chunks = []
    for chunk_id in chunk_ids:
        if chunk_id in found:
            chunks.append(found[chunk_id])
    return chunks
