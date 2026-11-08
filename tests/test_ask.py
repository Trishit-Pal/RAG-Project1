from core.ask import build_prompt, normalize_question, question_key


def test_normalize_question_collapses_case_and_spaces():
    assert normalize_question("  What   IS x? ") == "what is x?"


def test_question_key_matches_for_equivalent_questions():
    assert question_key("What  is X?") == question_key("what is x?")


def test_build_prompt_numbers_the_sources():
    prompt = build_prompt("Q?", [{"text": "alpha"}, {"text": "beta"}])
    assert "[1] alpha" in prompt
    assert "[2] beta" in prompt

def _fake_chunk(chunk_id=1, similarity=0.9):
    return {"chunk_id": chunk_id, "document_id": "d", "text": "t", "similarity": similarity}


def test_ask_cached_answer_still_returns_chunks(monkeypatch):
    from core import ask as ask_module

    monkeypatch.setattr(ask_module, "current_corpus_version", lambda: 1)
    monkeypatch.setattr(
        ask_module, "get_cached",
        lambda key, version: {"answer": "A", "chunk_ids": [5], "cached": True, "model": "m"},
    )
    monkeypatch.setattr(ask_module, "get_chunks_by_ids", lambda ids: [_fake_chunk(5, None)])

    result = ask_module.ask("q")

    assert result["cached"] is True
    assert result["chunks"][0]["chunk_id"] == 5  # same shape as a fresh answer


def test_ask_fresh_answer_saves_the_model_that_answered(monkeypatch):
    from core import ask as ask_module

    saved = {}
    monkeypatch.setattr(ask_module, "current_corpus_version", lambda: 1)
    monkeypatch.setattr(ask_module, "get_cached", lambda key, version: None)
    monkeypatch.setattr(ask_module, "retrieve", lambda q: [_fake_chunk()])
    monkeypatch.setattr(ask_module, "generate_text", lambda prompt: ("answer [1]", "model-x"))
    monkeypatch.setattr(ask_module, "save_trace", lambda *args: saved.update(args=args))

    result = ask_module.ask("q")

    assert result["model"] == "model-x"
    assert saved["args"][5] == "model-x"  # a database column that cannot be empty


def test_ask_with_no_matching_passages_does_not_call_gemini(monkeypatch):
    from core import ask as ask_module

    monkeypatch.setattr(ask_module, "current_corpus_version", lambda: 1)
    monkeypatch.setattr(ask_module, "get_cached", lambda key, version: None)
    monkeypatch.setattr(ask_module, "retrieve", lambda q: [])  # retrieve() drops weak matches

    def boom(prompt):
        raise AssertionError("Gemini should not be called")

    monkeypatch.setattr(ask_module, "generate_text", boom)

    assert ask_module.ask("q")["answer"] == ask_module.NOT_FOUND


def test_cited_numbers_finds_every_source_the_answer_mentions():
    from core.ask import cited_numbers

    assert cited_numbers("Revenue rose [1], costs fell [3][1].") == {1, 3}


def test_cited_numbers_is_empty_when_nothing_is_cited():
    from core.ask import cited_numbers

    assert cited_numbers("I don't know from the provided sources.") == set()


def test_get_cached_returns_none_when_nothing_is_saved(monkeypatch):
    from core import ask as ask_module

    monkeypatch.setattr(ask_module, "fetch_all", lambda sql, params=(): [])
    assert ask_module.get_cached("key", 1) is None


def test_get_cached_returns_the_saved_answer(monkeypatch):
    from core import ask as ask_module

    monkeypatch.setattr(ask_module, "fetch_all", lambda sql, params=(): [("A [1]", [4, 5], "m")])
    cached = ask_module.get_cached("key", 1)
    assert cached == {"answer": "A [1]", "chunk_ids": [4, 5], "model": "m", "cached": True}


def test_cached_answer_is_ignored_when_a_cited_passage_is_gone(monkeypatch):
    # Otherwise the remaining sources get renumbered and [2] points at the wrong passage.
    from core import ask as ask_module

    monkeypatch.setattr(ask_module, "current_corpus_version", lambda: 1)
    monkeypatch.setattr(
        ask_module, "get_cached",
        lambda key, version: {"answer": "A [2]", "chunk_ids": [10, 11], "cached": True, "model": "m"},
    )
    monkeypatch.setattr(ask_module, "get_chunks_by_ids", lambda ids: [_fake_chunk(10, None)])
    monkeypatch.setattr(ask_module, "retrieve", lambda q: [])  # fresh search finds nothing

    result = ask_module.ask("q")

    assert result["cached"] is False
