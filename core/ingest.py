"""Phase 5: ingest files and API data into the RAG corpus.

Run from the project root with the venv active:
    python -m core.ingest file data/sample.csv --source my-csv
    python -m core.ingest api --source open-meteo-paris
    python -m core.ingest status

Pipeline for each document:
    read -> hash -> skip if seen -> parse -> validate -> score
    -> (quarantine OR chunk + mask PII + embed + save)
"""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from core.chunk import chunk_rows, chunk_text
from core.db import bump_corpus_version, fetch_all, get_connection
from core.embed import DIM, MODEL, embed_texts
from core.parse import parse_csv, parse_docx, parse_pdf, parse_txt
from core.quality import insert_quality_run, score_pages, score_table
from core.stats import current_corpus_version, overview
from core.validate import mask_pii, validate_csv, validate_pages
from core.vectors import to_vector_literal


# Texts per embedding request. Small batches are gentler on the free tier (judgment).
EMBED_BATCH = 50

# File types that become a list of text "pages": extension -> (mime type, parser).
PAGE_FILE_TYPES = {
    ".pdf": ("application/pdf", parse_pdf),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        parse_docx,
    ),
    ".txt": ("text/plain", parse_txt),
}
# Every file type the app accepts. The upload page and save_upload() use this list too.
SUPPORTED_TYPES = {".csv", *PAGE_FILE_TYPES}

MAX_TRIES = 3


def fetch_api(url: str, params: dict) -> bytes:
    """Download a web address and return the raw answer.

    Network problems (no connection, timeout) are tried 3 times, 5 seconds apart.
    """
    full_url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, MAX_TRIES + 1):
        try:
            with urllib.request.urlopen(full_url, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError:
            # The server answered with an error (like 404 or 500). Trying again will not help.
            # This check must come first: HTTPError is a special kind of URLError.
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == MAX_TRIES:
                raise
            time.sleep(5)


# Public API sources. Open-Meteo needs no API key.
# Free for non-commercial use; attribution is required (https://open-meteo.com/).
API_SOURCES = {
    "open-meteo-paris": {
        "url": "https://api.open-meteo.com/v1/forecast",
        "params": {
            "latitude": 48.85,
            "longitude": 2.35,
            "hourly": "temperature_2m,precipitation,wind_speed_10m",
            "forecast_days": 3,
            "timezone": "Europe/Paris",
        },
    },
}


# ---------- small helpers ----------

def sha256_bytes(data: bytes) -> str:
    # The same input always gives the same fingerprint. Used to detect duplicates.
    return hashlib.sha256(data).hexdigest()


def document_exists(sha: str) -> bool:
    rows = fetch_all("select 1 from documents where content_sha256 = %s", (sha,))
    return len(rows) > 0


def get_or_create_source(name: str, kind: str, uri: str | None = None):
    # Return the id of the source with this name. Create it if it does not exist.
    with get_connection() as conn:
        row = conn.execute("select id from sources where name = %s", (name,)).fetchone()
        if row is None:
            row = conn.execute(
                "insert into sources (name, kind, uri) "
                "values (%s, %s::source_kind, %s) returning id",
                (name, kind, uri),
            ).fetchone()
    return row[0]


def hourly_to_frame(data: dict) -> pd.DataFrame:
    # Open-Meteo returns {"hourly": {"time": [...], "temperature_2m": [...], ...}}.
    # Each key becomes a column and each list becomes that column's values.
    return pd.DataFrame(data["hourly"])


def embed_all(texts: list[str]) -> list[list[float]]:
    # Embed in batches. Stored documents use the RETRIEVAL_DOCUMENT task type.
    vectors = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start:start + EMBED_BATCH]
        vectors.extend(embed_texts(batch, task_type="RETRIEVAL_DOCUMENT"))
    return vectors


# ---------- saving to the database ----------

def _insert_document(conn, source_id, sha, filename, mime_type, byte_size, status) -> object:
    # The database requires an embedding model on every document row,
    # so quarantined documents record the current one as well.
    model = MODEL
    dim = DIM
    row = conn.execute(
        """
        insert into documents
            (source_id, content_sha256, filename, mime_type, byte_size,
             status, embedding_model, embedding_dim)
        values (%s, %s, %s, %s, %s, %s::doc_status, %s, %s)
        returning id
        """,
        (source_id, sha, filename, mime_type, byte_size, status, model, dim),
    ).fetchone()
    return row[0]


def index_texts(source_id, filename, mime_type, byte_size, sha, texts, quality) -> tuple[str, str]:
    # 1. Mask personal data first, so the masked text is what gets stored.
    texts = [mask_pii(t) for t in texts]

    # 2. Embed BEFORE writing to the database. If Gemini fails, nothing is saved.
    vectors = embed_all(texts)

    # 3. Write everything in one transaction. The "with" block commits on exit.
    with get_connection() as conn:
        doc_id = _insert_document(
            conn, source_id, sha, filename, mime_type, byte_size, "indexed"
        )
        rows = [
            (doc_id, i, text, sha256_bytes(text.encode("utf-8")), to_vector_literal(vec))
            # strict=True raises an error if the two lists differ in length,
            # instead of quietly dropping the extra texts.
            for i, (text, vec) in enumerate(zip(texts, vectors, strict=True))
        ]
        # executemany sends all rows together instead of one network trip per chunk.
        with conn.cursor() as cur:
            cur.executemany(
                """
                insert into chunks (document_id, chunk_index, text, content_sha256, embedding)
                values (%s, %s, %s, %s, %s::vector)
                """,
                rows,
            )
        insert_quality_run(conn, source_id, quality)
        # Tell the answer cache that the documents changed.
        bump_corpus_version(conn)

    return "indexed", f"{filename}: {len(texts)} chunks"


def store_quarantined(source_id, filename, mime_type, byte_size, sha, rule, reasons, quality) -> None:
    # Quarantined files keep a document row, so re-runs skip them.
    # They get no chunks and no embeddings.
    with get_connection() as conn:
        doc_id = _insert_document(
            conn, source_id, sha, filename, mime_type, byte_size, "quarantined"
        )
        for reason in reasons:
            conn.execute(
                "insert into quarantine (document_id, locator, rule, severity, reason) "
                "values (%s, %s, %s, 'error', %s)",
                (doc_id, filename, rule, reason),
            )
        insert_quality_run(conn, source_id, quality)


# ---------- the two ingest paths ----------
# Both return (outcome, detail). outcome is one of: indexed, skipped,
# quarantined, rejected, error. detail is a short sentence for people.

def ingest_file(path_str: str, source_name: str) -> tuple[str, str]:
    path = Path(path_str)
    if not path.exists():
        return "error", f"file not found: {path}"

    raw = path.read_bytes()
    sha = sha256_bytes(raw)
    if document_exists(sha):
        return "skipped", f"{path.name} was already stored"

    suffix = path.suffix.lower()
    rule = f"{suffix.lstrip('.')}_validation"
    if suffix == ".csv":
        mime_type = "text/csv"
        df = parse_csv(path)
        result = validate_csv(df)
        quality = score_table(df, passed=result.ok)
        texts = chunk_rows(df) if result.ok else []
    elif suffix in PAGE_FILE_TYPES:
        # PDF, Word and text files are all lists of "pages" of text.
        mime_type, parser = PAGE_FILE_TYPES[suffix]
        pages = parser(path)
        result = validate_pages(pages)
        quality = score_pages(pages, passed=result.ok)
        # Split each page into chunks, then flatten the list.
        texts = [c for page in pages for c in chunk_text(page)] if result.ok else []
    else:
        return "rejected", f"unsupported file type '{suffix}' (use {', '.join(sorted(SUPPORTED_TYPES))})"

    # Uploaded files do not store a URI, so local paths are not saved.
    source_id = get_or_create_source(source_name, "upload")

    if not result.ok:
        store_quarantined(
            source_id, path.name, mime_type, len(raw), sha, rule, result.reasons, quality
        )
        return "quarantined", f"{path.name}: {'; '.join(result.reasons)}"

    return index_texts(source_id, path.name, mime_type, len(raw), sha, texts, quality)


def ingest_api(source_name: str) -> tuple[str, str]:
    config = API_SOURCES[source_name]  # raises KeyError for an unknown name
    raw = fetch_api(config["url"], config["params"])
    sha = sha256_bytes(raw)
    if document_exists(sha):
        return "skipped", f"the latest {source_name} data is already stored"

    df = hourly_to_frame(json.loads(raw))
    result = validate_csv(df)
    quality = score_table(df, passed=result.ok)
    source_id = get_or_create_source(source_name, "api", uri=config["url"])
    filename = f"{source_name}.json"

    if not result.ok:
        store_quarantined(
            source_id, filename, "application/json", len(raw), sha,
            "api_validation", result.reasons, quality,
        )
        return "quarantined", f"{source_name}: {'; '.join(result.reasons)}"

    # Each hourly row becomes one chunk, like a CSV row.
    return index_texts(
        source_id, filename, "application/json", len(raw), sha,
        chunk_rows(df), quality,
    )


def show_status() -> None:
    counts = overview()["documents"]
    if not counts:
        print("no documents yet")
    for status, count in sorted(counts.items()):
        print(f"{status}: {count}")
    print(f"corpus_version: {current_corpus_version()}")


# ---------- command line ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest data into the RAG corpus")
    sub = parser.add_subparsers(dest="command", required=True)

    p_file = sub.add_parser("file", help="ingest a local CSV, PDF, Word or text file")
    p_file.add_argument("path")
    p_file.add_argument("--source", required=True)

    p_api = sub.add_parser("api", help="ingest a configured API source")
    p_api.add_argument("--source", required=True, choices=sorted(API_SOURCES))

    sub.add_parser("status", help="show document counts")

    args = parser.parse_args()
    if args.command == "file":
        print(": ".join(ingest_file(args.path, args.source)))
    elif args.command == "api":
        print(": ".join(ingest_api(args.source)))
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()