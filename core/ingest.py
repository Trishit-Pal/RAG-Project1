"""Add files and live API data to the searchable library.

Used by the Upload page. Also runs on its own from the project folder:
    python -m core.ingest file data/sample.csv --source my-csv
    python -m core.ingest api --source open-meteo-paris
    python -m core.ingest status

Steps for every document:
    read -> fingerprint -> skip if already stored -> check -> score
    -> set aside (if it has problems)  OR  cut into chunks -> hide personal data -> embed -> save
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
from core.db import bump_corpus_version, fetch_all, get_connection, to_vector_text
from core.embed import DIM, MODEL, embed_texts
from core.parse import parse_csv, parse_docx, parse_pdf, parse_txt
from core.quality import insert_quality_run, score_pages, score_table
from core.stats import current_corpus_version, overview
from core.validate import mask_pii, validate_csv, validate_pages

EMBED_BATCH = 50  # texts per request to Gemini; small batches are gentler on the free tier
MAX_TRIES = 3

# File types that become a list of text pages: extension -> (file type name, reader function).
PAGE_FILE_TYPES = {
    ".pdf": ("application/pdf", parse_pdf),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", parse_docx),
    ".txt": ("text/plain", parse_txt),
}
# Every file type the app accepts: CSV plus every page type above, so a new reader
# added to PAGE_FILE_TYPES is accepted everywhere. The Upload page and save_upload() use it.
SUPPORTED_TYPES = [".csv"] + sorted(PAGE_FILE_TYPES)

# Live data sources. Open-Meteo needs no key.
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


def sha256_bytes(data: bytes) -> str:
    # A fingerprint: the same content always gives the same text. Used to spot duplicates.
    return hashlib.sha256(data).hexdigest()


def document_exists(sha: str) -> bool:
    rows = fetch_all("select 1 from documents where content_sha256 = %s", (sha,))
    return len(rows) > 0


def get_or_create_source(name: str, kind: str, uri: str = None):
    """Return the id of the source (group) with this name. Create it if it is new."""
    with get_connection() as conn:
        row = conn.execute("select id from sources where name = %s", (name,)).fetchone()
        if row is None:
            row = conn.execute(
                "insert into sources (name, kind, uri) values (%s, %s::source_kind, %s) returning id",
                (name, kind, uri),
            ).fetchone()
    return row[0]


def hourly_to_frame(data: dict) -> pd.DataFrame:
    # Open-Meteo returns {"hourly": {"time": [...], "temperature_2m": [...], ...}}.
    # Each key becomes a column and each list becomes that column's values.
    return pd.DataFrame(data["hourly"])


def embed_all(texts: list[str]) -> list[list[float]]:
    """Embed all texts, EMBED_BATCH at a time."""
    vectors = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start:start + EMBED_BATCH]
        vectors.extend(embed_texts(batch, task_type="RETRIEVAL_DOCUMENT"))
    return vectors


# ---------- saving to the database ----------

def insert_document(conn, source_id, sha, filename, mime_type, byte_size, status):
    # The database needs an embedding model on every document row,
    # so documents that were set aside record it too.
    row = conn.execute(
        """
        insert into documents
            (source_id, content_sha256, filename, mime_type, byte_size, status, embedding_model, embedding_dim)
        values (%s, %s, %s, %s, %s, %s::doc_status, %s, %s)
        returning id
        """,
        (source_id, sha, filename, mime_type, byte_size, status, MODEL, DIM),
    ).fetchone()
    return row[0]


def index_texts(source_id, filename, mime_type, byte_size, sha, texts, quality) -> tuple[str, str]:
    """Hide personal data, embed every chunk, and save it all. Returns ("indexed", detail)."""
    # 1. Hide personal data first, so the hidden version is what gets stored.
    clean_texts = []
    for text in texts:
        clean_texts.append(mask_pii(text))

    # 2. Embed BEFORE writing anything. If Gemini fails, nothing is saved.
    vectors = embed_all(clean_texts)

    # 3. Save everything together. If any step fails, nothing is saved.
    with get_connection() as conn:
        document_id = insert_document(conn, source_id, sha, filename, mime_type, byte_size, "indexed")

        # One row per chunk. strict=True stops with an error if the two lists
        # differ in length, instead of quietly dropping the extra texts.
        rows = []
        position = 0
        for text, vector in zip(clean_texts, vectors, strict=True):
            rows.append((document_id, position, text, sha256_bytes(text.encode("utf-8")), to_vector_text(vector)))
            position += 1

        with conn.cursor() as cur:
            # executemany sends all rows together instead of one network trip per chunk.
            cur.executemany(
                """
                insert into chunks (document_id, chunk_index, text, content_sha256, embedding)
                values (%s, %s, %s, %s, %s::vector)
                """,
                rows,
            )
        insert_quality_run(conn, source_id, quality)
        bump_corpus_version(conn)  # saved answers are now out of date

    return "indexed", f"{filename}: {len(clean_texts)} chunks"


def store_quarantined(source_id, filename, mime_type, byte_size, sha, rule, problems, quality) -> None:
    # Files that were set aside keep a document row, so uploading them again is skipped.
    # They get no chunks and no vectors.
    with get_connection() as conn:
        document_id = insert_document(conn, source_id, sha, filename, mime_type, byte_size, "quarantined")
        for problem in problems:
            conn.execute(
                "insert into quarantine (document_id, locator, rule, severity, reason) values (%s, %s, %s, 'error', %s)",
                (document_id, filename, rule, problem),
            )
        insert_quality_run(conn, source_id, quality)


# ---------- the two ways in: a file, or a live API ----------
# Both return (outcome, detail). outcome is one of: indexed, skipped,
# quarantined, rejected, error. detail is a short sentence for people.

def read_file(path: Path):
    """Open and check a supported file. Returns (mime type, problems, quality, chunks)."""
    extension = path.suffix.lower()
    if extension == ".csv":
        df = parse_csv(path)
        problems = validate_csv(df)
        quality = score_table(df, passed=not problems)
        chunks = chunk_rows(df) if not problems else []
        return "text/csv", problems, quality, chunks

    # PDF, Word and text files all become a list of text pages.
    mime_type, reader = PAGE_FILE_TYPES[extension]
    pages = reader(path)
    problems = validate_pages(pages)
    quality = score_pages(pages, passed=not problems)
    chunks = []
    if not problems:
        for page in pages:
            chunks.extend(chunk_text(page))
    return mime_type, problems, quality, chunks


def ingest_file(path_text: str, source_name: str) -> tuple[str, str]:
    path = Path(path_text)
    if not path.exists():
        return "error", f"file not found: {path}"
    if path.suffix.lower() not in SUPPORTED_TYPES:
        return "rejected", f"unsupported file type '{path.suffix}' (use {', '.join(SUPPORTED_TYPES)})"

    raw = path.read_bytes()
    sha = sha256_bytes(raw)
    if document_exists(sha):
        return "skipped", f"{path.name} was already stored"

    mime_type, problems, quality, chunks = read_file(path)
    # Uploaded files do not store their local path.
    source_id = get_or_create_source(source_name, "upload")
    rule = path.suffix.lower().lstrip(".") + "_validation"  # for example "csv_validation"

    if problems:
        store_quarantined(source_id, path.name, mime_type, len(raw), sha, rule, problems, quality)
        return "quarantined", f"{path.name}: {'; '.join(problems)}"
    return index_texts(source_id, path.name, mime_type, len(raw), sha, chunks, quality)


def ingest_api(source_name: str) -> tuple[str, str]:
    config = API_SOURCES[source_name]
    raw = fetch_api(config["url"], config["params"])
    sha = sha256_bytes(raw)
    if document_exists(sha):
        return "skipped", f"the latest {source_name} data is already stored"

    df = hourly_to_frame(json.loads(raw))
    problems = validate_csv(df)
    quality = score_table(df, passed=not problems)
    source_id = get_or_create_source(source_name, "api", uri=config["url"])
    filename = f"{source_name}.json"

    if problems:
        store_quarantined(source_id, filename, "application/json", len(raw), sha, "api_validation", problems, quality)
        return "quarantined", f"{source_name}: {'; '.join(problems)}"
    # Each hourly row becomes one chunk, like a CSV row.
    return index_texts(source_id, filename, "application/json", len(raw), sha, chunk_rows(df), quality)


def show_status() -> None:
    counts = overview()["documents"]
    if not counts:
        print("no documents yet")
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")
    print(f"corpus_version: {current_corpus_version()}")


# ---------- command line ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="Add data to the searchable library")
    commands = parser.add_subparsers(dest="command", required=True)

    file_command = commands.add_parser("file", help="add a local CSV, PDF, Word or text file")
    file_command.add_argument("path")
    file_command.add_argument("--source", required=True)

    api_command = commands.add_parser("api", help="add the latest data from a live API")
    api_command.add_argument("--source", required=True, choices=sorted(API_SOURCES))

    commands.add_parser("status", help="show document counts")

    args = parser.parse_args()
    if args.command == "file":
        outcome, detail = ingest_file(args.path, args.source)
        print(f"{outcome}: {detail}")
    elif args.command == "api":
        outcome, detail = ingest_api(args.source)
        print(f"{outcome}: {detail}")
    else:
        show_status()


if __name__ == "__main__":
    main()
