import psycopg

from core.config import settings


def get_connection() -> psycopg.Connection:
    return psycopg.connect(settings.DATABASE_URL)


def fetch_all(sql: str, params: tuple = ()) -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def rows_to_dicts(names: list[str], rows: list[tuple]) -> list[dict]:
    # Turn database rows into dictionaries: easier to read and to put in a table.
    return [dict(zip(names, row)) for row in rows]


def bump_corpus_version(conn) -> None:
    # Cached answers are only valid for one corpus version. Raising it makes
    # every saved answer stale. Called after new documents are added, and when
    # someone clicks "Forget saved answers".
    conn.execute("update corpus_state set corpus_version = corpus_version + 1 where id = 1")
