from core.db import rows_to_dicts, to_vector_text


def test_to_vector_text_formats_a_list_of_numbers():
    assert to_vector_text([0.5, 1]) == "[0.5,1.0]"


def test_rows_to_dicts_names_each_value():
    assert rows_to_dicts(["a", "b"], [(1, 2), (3, 4)]) == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]


import psycopg
import pytest

from core import db


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params):
        if self.conn.broken:
            raise psycopg.OperationalError("server closed the connection")
        if "bad sql" in sql:
            raise psycopg.errors.SyntaxError("syntax error")

    def fetchall(self):
        return [("ok",)]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConnection:
    def __init__(self, broken=False):
        self.broken = broken
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


@pytest.fixture
def opened(monkeypatch):
    # Count every new connection instead of opening real ones.
    connections = []

    def fake_open():
        connection = FakeConnection()
        connections.append(connection)
        return connection

    monkeypatch.setattr(db, "open_reading_connection", fake_open)
    monkeypatch.setattr(db, "shared", {"connection": None})
    return connections


def test_fetch_all_reuses_one_connection(opened):
    db.fetch_all("select 1")
    db.fetch_all("select 2")
    assert len(opened) == 1


def test_fetch_all_reopens_a_dropped_connection(opened):
    db.fetch_all("select 1")
    opened[0].broken = True  # the server dropped it while idle

    assert db.fetch_all("select 1") == [("ok",)]
    assert len(opened) == 2


def test_fetch_all_does_not_retry_a_mistake_in_the_query(opened):
    with pytest.raises(psycopg.errors.SyntaxError):
        db.fetch_all("bad sql")
    assert len(opened) == 1


def test_a_cancelled_slow_query_is_not_retried_and_keeps_the_connection(opened):
    db.fetch_all("select 1")
    first = opened[0]
    first.broken = False

    def cancelled(sql, params):
        raise psycopg.errors.QueryCanceled("canceling statement due to statement timeout")

    original_cursor = first.cursor
    first.cursor = lambda: type("C", (), {"execute": staticmethod(cancelled), "__enter__": lambda self: self,
                                          "__exit__": lambda self, *exc: False})()
    with pytest.raises(psycopg.errors.QueryCanceled):
        db.fetch_all("select pg_sleep(60)")
    first.cursor = original_cursor
    assert len(opened) == 1  # no new connection was opened


def test_a_dropped_connection_is_closed_before_it_is_replaced(opened):
    db.fetch_all("select 1")
    opened[0].broken = True
    db.fetch_all("select 1")
    assert opened[0].closed is True


def test_reading_connection_has_timeouts_and_works_with_any_pooler(monkeypatch):
    seen = {"commands": []}

    class RecordingConnection:
        def execute(self, sql):
            seen["commands"].append(sql)

    def fake_connect(url, **settings):
        seen.update(settings)
        return RecordingConnection()

    monkeypatch.setattr(db, "DATABASE_URL", "postgresql://example")
    monkeypatch.setattr(db.psycopg, "connect", fake_connect)

    db.open_reading_connection()

    assert seen["autocommit"] is True
    assert seen["connect_timeout"] > 0
    assert seen["prepare_threshold"] is None  # transaction poolers cannot keep prepared statements
    # Set as a command: Supabase's pooler ignores it when passed while connecting.
    assert seen["commands"] == [f"set statement_timeout = {db.READ_TIMEOUT_MS}"]
