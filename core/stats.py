"""Read-only database helpers used by the Streamlit pages.

Nothing here changes the database. Each function returns plain lists and
dictionaries, so the pages stay short and easy to read.
"""
from core.db import fetch_all


def get_chunks_by_ids(chunk_ids: list[int]) -> list[dict]:
    # Used for cached answers, which only remember which chunks were used.
    if not chunk_ids:
        return []
    rows = fetch_all(
        "select id, document_id, text from chunks where id = any(%s)", (chunk_ids,)
    )
    by_id = {row[0]: row for row in rows}
    # Keep the original order, so the sources still match the [1], [2] numbers.
    return [
        {
            "chunk_id": cid,
            "document_id": by_id[cid][1],
            "text": by_id[cid][2],
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
