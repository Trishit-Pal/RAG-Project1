from core import retrieve as retrieve_module


def test_retrieve_casts_arguments_to_the_types_match_chunks_expects(monkeypatch):
    # psycopg sends Python numbers as smallint / double precision, and Postgres
    # then cannot find match_chunks(vector, integer, real). The casts prevent that.
    seen = {}
    monkeypatch.setattr(retrieve_module, "embed_texts", lambda texts, task_type: [[0.1, 0.2]])
    monkeypatch.setattr(
        retrieve_module, "fetch_all", lambda sql, params=(): seen.update(sql=sql) or []
    )

    retrieve_module.retrieve("question")

    assert "%s::int" in seen["sql"]
    assert "%s::real" in seen["sql"]


def test_retrieve_drops_weak_matches(monkeypatch):
    # Answers and evaluation both rely on this cut-off.
    monkeypatch.setattr(retrieve_module, "embed_texts", lambda texts, task_type: [[0.1]])
    rows = [(1, "doc-1", "close", 0.8, 0.9), (2, "doc-2", "far away", 0.1, 0.9)]
    monkeypatch.setattr(retrieve_module, "fetch_all", lambda sql, params=(): rows)

    assert [c["chunk_id"] for c in retrieve_module.retrieve("question")] == [1]


def test_retrieve_returns_dictionaries(monkeypatch):
    monkeypatch.setattr(retrieve_module, "embed_texts", lambda texts, task_type: [[0.1]])
    row = (7, "doc-1", "some text", 0.8, None)
    monkeypatch.setattr(retrieve_module, "fetch_all", lambda sql, params=(): [row])

    chunks = retrieve_module.retrieve("question")

    assert chunks == [{
        "chunk_id": 7, "document_id": "doc-1", "text": "some text",
        "similarity": 0.8, "source_quality": 0.0,
    }]
