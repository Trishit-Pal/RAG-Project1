"""Talk to the Postgres database (hosted on Supabase).

Every file that reads or writes data uses these few functions.

Opening a connection to the database takes about 2 seconds, so reading reuses
one open connection instead of opening a new one for every query.
Writing opens its own connection, so a save is all-or-nothing.
"""
import threading

import psycopg

from core.config import DATABASE_URL

# The one connection used for reading, kept open between queries.
shared = {"connection": None}
# Streamlit serves each visitor in its own thread. The lock makes them take
# turns, because one connection can only run one query at a time.
reading_lock = threading.Lock()


def get_connection() -> psycopg.Connection:
    # For writing. Use it in a "with" block: changes are saved when the block
    # ends without an error, and the connection is then closed.
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Add it to your .env file.")
    return psycopg.connect(DATABASE_URL)


def open_reading_connection() -> psycopg.Connection:
    # autocommit=True: each read stands alone, so the connection never sits in
    # an unfinished transaction between visitors.
    connection = get_connection()
    connection.autocommit = True
    return connection


def fetch_all(sql: str, params: tuple = ()) -> list[tuple]:
    """Run a query and return every row it finds. Each row is a tuple."""
    with reading_lock:
        for attempt in (1, 2):
            if shared["connection"] is None:
                shared["connection"] = open_reading_connection()
            try:
                with shared["connection"].cursor() as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
            except psycopg.OperationalError:
                # The connection was dropped (for example after a long quiet spell).
                # Forget it and open a fresh one, once.
                shared["connection"] = None
                if attempt == 2:
                    raise


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
