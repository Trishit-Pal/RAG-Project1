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
    monkeypatch.setattr(ask_module, "attach_filenames", lambda chunks: chunks)

    result = ask_module.ask("q")

    assert result["cached"] is True
    assert result["chunks"][0]["chunk_id"] == 5  # same shape as a fresh answer


def test_ask_fresh_answer_saves_the_model_that_answered(monkeypatch):
    from core import ask as ask_module

    saved = {}
    monkeypatch.setattr(ask_module, "current_corpus_version", lambda: 1)
    monkeypatch.setattr(ask_module, "get_cached", lambda key, version: None)
    monkeypatch.setattr(ask_module, "retrieve", lambda q: [_fake_chunk()])
    monkeypatch.setattr(ask_module, "attach_filenames", lambda chunks: chunks)
    monkeypatch.setattr(ask_module, "generate_text", lambda prompt: ("answer [1]", "model-x"))
    monkeypatch.setattr(ask_module, "save_trace", lambda *args: saved.update(args=args))

    result = ask_module.ask("q")

    assert result["model"] == "model-x"
    assert saved["args"][5] == "model-x"  # a database column that cannot be empty


def test_ask_with_only_weak_matches_does_not_call_gemini(monkeypatch):
    from core import ask as ask_module

    monkeypatch.setattr(ask_module, "current_corpus_version", lambda: 1)
    monkeypatch.setattr(ask_module, "get_cached", lambda key, version: None)
    monkeypatch.setattr(ask_module, "retrieve", lambda q: [_fake_chunk(similarity=0.1)])

    def boom(prompt):
        raise AssertionError("Gemini should not be called")

    monkeypatch.setattr(ask_module, "generate_text", boom)

    assert ask_module.ask("q")["answer"] == ask_module.NOT_FOUND
