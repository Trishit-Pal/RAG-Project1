"""Talk to the Postgres database (hosted on Supabase).

Every file that reads or writes data uses these few functions.
"""
import psycopg

from core.config import DATABASE_URL


def get_connection() -> psycopg.Connection:
    # Use it in a "with" block. Changes are saved when the block ends without an error.
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Add it to your .env file.")
    return psycopg.connect(DATABASE_URL)


def fetch_all(sql: str, params: tuple = ()) -> list[tuple]:
    """Run a query and return every row it finds. Each row is a tuple."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def rows_to_dicts(names: list[str], rows: list[tuple]) -> list[dict]:
    """Turn rows into dictionaries, so code can say row["filename"] instead of row[0]."""
    result = []
    for row in rows:
        # zip pairs each name with the value in the same position.
        result.append(dict(zip(names, row)))
    return result


def to_vector_text(numbers: list[float]) -> str:
    # The database stores vectors as text like "[0.1,0.2,0.3]".
    parts = []
    for number in numbers:
        parts.append(str(float(number)))
    return "[" + ",".join(parts) + "]"


def bump_corpus_version(conn) -> None:
    # Saved answers are only reused while this number stays the same.
    # Called after new documents are added, and by "Forget saved answers".
    conn.execute("update corpus_state set corpus_version = corpus_version + 1 where id = 1")
