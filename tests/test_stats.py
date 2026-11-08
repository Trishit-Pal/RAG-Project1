from core import stats


def test_get_chunks_by_ids_keeps_the_requested_order(monkeypatch):
    # The database returns rows in any order; sources must keep their [1], [2] order.
    rows = [(2, "doc-b", "second", "b.pdf"), (1, "doc-a", "first", "a.pdf")]
    monkeypatch.setattr(stats, "fetch_all", lambda sql, params=(): rows)

    chunks = stats.get_chunks_by_ids([1, 2])

    assert [c["chunk_id"] for c in chunks] == [1, 2]
    assert chunks[0]["text"] == "first"
    assert chunks[0]["filename"] == "a.pdf"


def test_get_chunks_by_ids_with_no_ids_skips_the_database(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("should not query the database")

    monkeypatch.setattr(stats, "fetch_all", boom)
    assert stats.get_chunks_by_ids([]) == []


def test_list_documents_returns_one_dictionary_per_row(monkeypatch):
    rows = [("a.pdf", "reports", "indexed", 1200, "2026-01-01", 5)]
    monkeypatch.setattr(stats, "fetch_all", lambda sql, params=(): rows)

    docs = stats.list_documents()

    assert docs == [{
        "filename": "a.pdf", "source": "reports", "status": "indexed",
        "size_bytes": 1200, "ingested_at": "2026-01-01", "chunks": 5,
    }]


def test_overview_combines_the_counts(monkeypatch):
    answers = iter([[("indexed", 2), ("quarantined", 1)], [(7, 3)]])
    monkeypatch.setattr(stats, "fetch_all", lambda sql, params=(): next(answers))

    overview = stats.overview()

    assert overview == {"documents": {"indexed": 2, "quarantined": 1}, "chunks": 7, "questions": 3}


import pytest


@pytest.mark.parametrize("function, row, first_key", [
    (stats.list_sources, ("id-1", "reports", "upload", 0.9), "id"),
    (stats.list_quarantine, ("a.csv", "csv_validation", "duplicate rows", "2026-01-01"), "filename"),
    (stats.list_quality_runs, ("reports", "2026-01-01", 2, 2, 1.0, 0.0, 1.0), "source"),
    (stats.recent_questions, ("q?", "a", "m", 120, "2026-01-01"), "question"),
])
def test_list_functions_name_every_column(monkeypatch, function, row, first_key):
    monkeypatch.setattr(stats, "fetch_all", lambda sql, params=(): [row])

    result = function()

    assert len(result[0]) == len(row)  # no column lost or unnamed
    assert result[0][first_key] == row[0]


def test_questions_per_day_names_each_column(monkeypatch):
    seen = {}

    def fake_fetch_all(sql, params=()):
        seen["params"] = params
        return [("2026-11-07", 3), ("2026-11-08", 5)]

    monkeypatch.setattr(stats, "fetch_all", fake_fetch_all)

    result = stats.questions_per_day(days=30)

    assert result == [{"day": "2026-11-07", "questions": 3}, {"day": "2026-11-08", "questions": 5}]
    assert seen["params"] == (30,)  # the time window is passed in, not pasted into the SQL
