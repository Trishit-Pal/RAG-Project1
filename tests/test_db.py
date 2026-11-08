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
