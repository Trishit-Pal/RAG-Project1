from core import evals


def test_hit_when_an_expected_source_is_retrieved():
    assert evals.is_hit(["src-a"], ["src-x", "src-a"]) is True


def test_miss_when_no_expected_source_is_retrieved():
    assert evals.is_hit(["src-a"], ["src-x", "src-y"]) is False


def test_miss_when_nothing_was_retrieved():
    assert evals.is_hit(["src-a"], []) is False


def test_summarize_computes_hit_rate_and_pass():
    metrics, passed = evals.summarize([True, True, True, False])  # 75% >= 70%
    assert metrics == {"cases": 4, "hits": 3, "hit_rate": 0.75}
    assert passed is True


def test_summarize_fails_below_the_pass_mark():
    _, passed = evals.summarize([True, False, False, False])  # 25%
    assert passed is False


def test_summarize_with_no_cases_does_not_divide_by_zero():
    metrics, passed = evals.summarize([])
    assert metrics["hit_rate"] == 0.0
    assert passed is False


def test_run_eval_scores_each_case_by_its_retrieved_sources(monkeypatch):
    cases = [
        {"id": 1, "question": "q1", "expected_source_ids": ["src-a"]},
        {"id": 2, "question": "q2", "expected_source_ids": ["src-b"]},
    ]
    monkeypatch.setattr(evals, "list_cases", lambda: cases)
    # Every passage found comes from src-a, so only case 1 is a hit.
    monkeypatch.setattr(evals, "retrieve", lambda q, k: [{"document_id": "doc-1", "source_id": "src-a"}])
    saved = {}
    monkeypatch.setattr(evals, "save_run", lambda metrics, passed: saved.update(m=metrics, p=passed))

    result = evals.run_eval()

    assert [r["hit"] for r in result["results"]] == [True, False]
    assert saved["m"]["hit_rate"] == 0.5
    assert saved["p"] is False


def test_list_cases_turns_rows_into_dictionaries(monkeypatch):
    monkeypatch.setattr(evals, "fetch_all", lambda sql, params=(): [(1, "q?", ("src-a",), None)])
    assert evals.list_cases() == [
        {"id": 1, "question": "q?", "expected_source_ids": ["src-a"], "reference_answer": None}
    ]


def test_run_eval_with_no_cases_saves_nothing(monkeypatch):
    def should_not_save(metrics, passed):
        raise AssertionError("an empty run should not be saved")

    monkeypatch.setattr(evals, "list_cases", lambda: [])
    monkeypatch.setattr(evals, "save_run", should_not_save)
    assert evals.run_eval()["passed"] is False

