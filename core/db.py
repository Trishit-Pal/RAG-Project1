"""Talk to the Postgres database (hosted on Supabase).

Every file that reads or writes data uses these few functions.

Opening a connection to the database takes about 2 seconds, so reading reuses
one open connection instead of opening a new one for every query.
Writing opens its own connection, so a save is all-or-nothing.
"""
import threading

import psycopg

from core.config import DATABASE_URL

CONNECT_TIMEOUT = 10    # seconds to wait for the database to answer a new connection
READ_TIMEOUT_MS = 15000  # stop any read that runs longer than 15 seconds

# The one connection used for reading, kept open between queries. It sits in a
# dictionary so the functions below can swap it for a new one.
shared = {"connection": None}
# Streamlit serves each visitor in its own thread. The lock makes them take
# turns, because one connection can only run one query at a time.
reading_lock = threading.Lock()


def check_database_url() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Add it to your .env file.")


def get_connection() -> psycopg.Connection:
    # For writing. Use it in a "with" block: changes are saved when the block
    # ends without an error, and the connection is then closed.
    check_database_url()
    return psycopg.connect(DATABASE_URL, connect_timeout=CONNECT_TIMEOUT)


def open_reading_connection() -> psycopg.Connection:
    """A connection for reading, with limits so one stuck query cannot freeze the app."""
    check_database_url()
    connection = psycopg.connect(
        DATABASE_URL,
        autocommit=True,                  # each read stands alone; never left half-finished
        connect_timeout=CONNECT_TIMEOUT,  # give up if the database does not answer
        prepare_threshold=None,           # needed for Supabase's "transaction pooler"
        keepalives=1,                     # these four notice a dead network quickly,
        keepalives_idle=30,               # instead of waiting minutes
        keepalives_interval=10,
        keepalives_count=3,
    )
    # Stop any read that runs too long. Set with a command, because Supabase's
    # pooler ignores this setting when it is passed while connecting.
    connection.execute(f"set statement_timeout = {READ_TIMEOUT_MS}")
    return connection


def run_query(sql: str, params: tuple) -> list[tuple]:
    # Use the shared connection, opening it first if there is none yet.
    if shared["connection"] is None:
        shared["connection"] = open_reading_connection()
    with shared["connection"].cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def forget_connection() -> None:
    # Close a broken connection so the next query opens a fresh one.
    try:
        shared["connection"].close()
    except Exception:
        pass  # it is already broken or missing; there is nothing more to close
    shared["connection"] = None


def fetch_all(sql: str, params: tuple = ()) -> list[tuple]:
    """Run a query and return every row it finds. Each row is a tuple."""
    with reading_lock:
        try:
            return run_query(sql, params)
        except psycopg.errors.QueryCanceled:
            # The query took too long and was stopped. The connection is fine, and
            # trying again would only be slow again, so pass the error on.
            raise
        except psycopg.OperationalError:
            # The connection was dropped (for example after a long quiet spell).
            # Close it, open a fresh one and try once more.
            forget_connection()
            return run_query(sql, params)


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
