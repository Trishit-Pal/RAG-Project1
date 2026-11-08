"""Read-only database helpers used by the Streamlit pages.

Nothing here changes the database. Each function returns plain lists and
dictionaries, so the pages stay short and easy to read.
"""
from core.db import fetch_all, rows_to_dicts


def current_corpus_version() -> int:
    # Goes up by 1 when documents are added or saved answers are cleared.
    # Cached answers are only reused while it stays the same.
    rows = fetch_all("select corpus_version from corpus_state where id = 1")
    return int(rows[0][0])


def count_indexed_documents() -> int:
    # One small query, for pages that only need to know "is anything stored?".
    return fetch_all("select count(*) from documents where status = 'indexed'")[0][0]


def overview() -> dict:
    # The numbers shown on the Home page.
    status_rows = fetch_all("select status::text, count(*) from documents group by status")
    # Two counts in one query: each query is a trip to the database.
    chunks, questions = fetch_all(
        "select (select count(*) from chunks), (select count(*) from query_traces)"
    )[0]
    return {
        "documents": {status: count for status, count in status_rows},
        "chunks": chunks,
        "questions": questions,
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
    return rows_to_dicts(
        ["filename", "source", "status", "size_bytes", "ingested_at", "chunks"], rows
    )


def list_sources() -> list[dict]:
    rows = fetch_all(
        "select id, name, kind::text, quality_score from sources order by name"
    )
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
        select s.name, r.run_at, r.rows_in, r.rows_passed,
               r.completeness, r.duplicate_rate, r.score
        from quality_runs r
        join sources s on s.id = r.source_id
        order by r.run_at desc
        limit %s
        """,
        (limit,),
    )
    return rows_to_dicts(
        ["source", "run_at", "rows_in", "rows_passed", "completeness", "duplicate_rate", "score"],
        rows,
    )


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
    # Used for cached answers, which only remember which chunks were used.
    if not chunk_ids:
        return []
    rows = fetch_all(
        "select c.id, c.document_id, c.text, d.filename "
        "from chunks c join documents d on d.id = c.document_id "
        "where c.id = any(%s)",
        (chunk_ids,),
    )
    by_id = {row[0]: row for row in rows}
    # Keep the original order, so the sources still match the [1], [2] numbers.
    return [
        {
            "chunk_id": cid,
            "document_id": by_id[cid][1],
            "text": by_id[cid][2],
            "filename": by_id[cid][3],
            "similarity": None,  # not saved with the cached answer
        }
        for cid in chunk_ids
        if cid in by_id
    ]


def attach_filenames(chunks: list[dict]) -> list[dict]:
    # Add the file name to each chunk so the page can show where it came from.
    document_ids = list({c["document_id"] for c in chunks})
    if not document_ids:
        return []
    rows = fetch_all(
        "select id, filename from documents where id = any(%s)", (document_ids,)
    )
    names = dict(rows)
    # Build new dictionaries instead of changing the ones we were given.
    return [{**c, "filename": names.get(c["document_id"], "unknown")} for c in chunks]
