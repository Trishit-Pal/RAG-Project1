"""Ingest write paths, tested with a fake database connection (no network, no Supabase)."""
import pytest

from core import embed, ingest


class FakeResult:
    def fetchone(self):
        return ("doc-1",)


class FakeCursor:
    # Stands in for a psycopg cursor. executemany records one call per row.
    def __init__(self, conn):
        self.conn = conn

    def executemany(self, sql, rows):
        for row in rows:
            self.conn.execute(sql, row)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    # Stands in for a psycopg connection: records SQL, supports "with".
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), params))
        return FakeResult()

    def cursor(self):
        return FakeCursor(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def sql_starting_with(self, start):
        return [c for c in self.calls if c[0].startswith(start)]


@pytest.fixture
def fake_db(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(ingest, "get_connection", lambda: conn)
    return conn


def fake_quality():
    return {"score": 1.0, "details": {"completeness": 1.0, "uniqueness": 1.0, "validity": 1.0},
            "rows_in": 2, "rows_passed": 2}


def test_index_texts_masks_pii_saves_chunks_and_bumps_the_corpus_version(fake_db, monkeypatch):
    monkeypatch.setattr(ingest, "embed_all", lambda texts: [[0.1, 0.2] for _ in texts])

    result = ingest.index_texts(
        "src-1", "a.txt", "text/plain", 10, "sha", ["mail me at a@b.com", "second"], fake_quality()
    )

    assert result == ("indexed", "a.txt: 2 chunks")
    chunk_inserts = fake_db.sql_starting_with("insert into chunks")
    assert len(chunk_inserts) == 2
    assert chunk_inserts[0][1][2] == "mail me at [EMAIL]"  # masked before saving
    assert fake_db.sql_starting_with("update corpus_state")  # cached answers become stale
    assert fake_db.sql_starting_with("insert into quality_runs")


def test_index_texts_saves_nothing_when_embedding_fails(fake_db, monkeypatch):
    def broken(texts):
        raise RuntimeError("Gemini down")

    monkeypatch.setattr(ingest, "embed_all", broken)

    with pytest.raises(RuntimeError):
        ingest.index_texts("src-1", "a.txt", "text/plain", 10, "sha", ["x"], fake_quality())
    assert fake_db.calls == []


def test_store_quarantined_saves_one_row_per_reason(fake_db):
    ingest.store_quarantined(
        "src-1", "bad.csv", "text/csv", 5, "sha", "csv_validation",
        ["duplicate rows", "too many empty cells"], fake_quality(),
    )

    assert len(fake_db.sql_starting_with("insert into quarantine")) == 2
    document_insert = fake_db.sql_starting_with("insert into documents")[0]
    assert document_insert[1][6] == ingest.MODEL  # embedding_model column cannot be empty


def test_embed_all_sends_texts_in_batches(monkeypatch):
    batches = []
    monkeypatch.setattr(ingest, "EMBED_BATCH", 2)
    monkeypatch.setattr(
        ingest, "embed_texts", lambda texts, task_type: batches.append(texts) or [[0.0]] * len(texts)
    )

    vectors = ingest.embed_all(["a", "b", "c"])

    assert batches == [["a", "b"], ["c"]]
    assert len(vectors) == 3


def test_ingest_api_skips_a_response_it_has_already_stored(monkeypatch):
    class FakeResponse:
        content = b'{"hourly": {"time": ["t1"], "temperature_2m": [1.0]}}'

    monkeypatch.setattr(ingest, "fetch_api", lambda url, params: FakeResponse())
    monkeypatch.setattr(ingest, "document_exists", lambda sha: True)

    assert ingest.ingest_api("open-meteo-paris")[0] == "skipped"


def test_normalize_makes_vectors_length_one():
    assert embed._12_normalize([3.0, 4.0]) == [0.6, 0.8]


def test_normalize_rejects_an_all_zero_vector():
    with pytest.raises(ValueError):
        embed._12_normalize([0.0, 0.0])


def test_embed_texts_rejects_an_unknown_task_type():
    with pytest.raises(ValueError):
        embed.embed_texts(["x"], task_type="SOMETHING_ELSE")


def test_embed_texts_with_no_texts_does_not_call_gemini():
    assert embed.embed_texts([], task_type="RETRIEVAL_QUERY") == []


class FakeEmbeddings:
    # Mimics Gemini: one vector per Content it is given.
    def __init__(self, vectors_to_return=None):
        self.vectors_to_return = vectors_to_return
        self.models = self

    def embed_content(self, model, contents, config):
        # Like the real API: a list of plain strings counts as ONE document.
        count = 1 if all(isinstance(c, str) for c in contents) else len(contents)
        if self.vectors_to_return is not None:
            count = self.vectors_to_return
        values = [type("E", (), {"values": [1.0, 0.0]})() for _ in range(count)]
        return type("R", (), {"embeddings": values})()


def test_embed_texts_returns_one_vector_per_text(monkeypatch):
    # Gemini reads a plain list of strings as ONE document and returns one vector.
    # Each text must be sent as its own Content to get one vector each.
    monkeypatch.setattr(embed, "client", FakeEmbeddings())
    assert len(embed.embed_texts(["a", "b", "c"], task_type="RETRIEVAL_DOCUMENT")) == 3


def test_embed_texts_fails_loudly_when_vectors_go_missing(monkeypatch):
    # Before this check, missing vectors silently dropped chunks (60 rows -> 2 stored).
    monkeypatch.setattr(embed, "client", FakeEmbeddings(vectors_to_return=1))
    with pytest.raises(RuntimeError, match="3 texts"):
        embed.embed_texts(["a", "b", "c"], task_type="RETRIEVAL_DOCUMENT")


def test_index_texts_refuses_to_save_when_counts_differ(fake_db, monkeypatch):
    monkeypatch.setattr(ingest, "embed_all", lambda texts: [[0.1]])  # 1 vector for 2 texts
    with pytest.raises(ValueError):
        ingest.index_texts("src-1", "a.txt", "text/plain", 10, "sha", ["one", "two"], fake_quality())
