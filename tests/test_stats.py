from core import stats


def test_get_chunks_by_ids_keeps_the_requested_order(monkeypatch):
    # The database returns rows in any order; sources must keep their [1], [2] order.
    rows = [(2, "doc-b", "second"), (1, "doc-a", "first")]
    monkeypatch.setattr(stats, "fetch_all", lambda sql, params=(): rows)

    chunks = stats.get_chunks_by_ids([1, 2])

    assert [c["chunk_id"] for c in chunks] == [1, 2]
    assert chunks[0]["text"] == "first"


def test_get_chunks_by_ids_with_no_ids_skips_the_database(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("should not query the database")

    monkeypatch.setattr(stats, "fetch_all", boom)
    assert stats.get_chunks_by_ids([]) == []


def test_attach_filenames_adds_a_name_without_changing_the_input(monkeypatch):
    monkeypatch.setattr(stats, "fetch_all", lambda sql, params=(): [("doc-a", "report.pdf")])
    original = [{"chunk_id": 1, "document_id": "doc-a", "text": "x"}]

    result = stats.attach_filenames(original)

    assert result[0]["filename"] == "report.pdf"
    assert "filename" not in original[0]  # the input list was not changed
