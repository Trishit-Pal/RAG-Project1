import psycopg
from core.config import settings

def get_connection() -> psycopg.Connection:
    return psycopg.connect(settings.DATABASE_URL)

def fetch_all(sql: str, params: tuple =()) -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def execute( sql: str, params: tuple= ()) ->None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql,params)
