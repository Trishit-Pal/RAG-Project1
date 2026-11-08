from core import generate


def test_generate_text_reports_the_main_model(monkeypatch):
    monkeypatch.setattr(generate, "call_model", lambda prompt, model: "hi")
    assert generate.generate_text("p") == ("hi", generate.MAIN_MODEL)


def test_generate_text_uses_the_backup_when_rate_limited(monkeypatch):
    def fake_call(prompt, model):
        if model == generate.MAIN_MODEL:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "from backup"

    monkeypatch.setattr(generate, "call_model", fake_call)
    assert generate.generate_text("p") == ("from backup", generate.BACKUP_MODEL)


class FakeModels:
    # Fails with a rate limit `failures` times, then answers.
    def __init__(self, failures, error_text="429 RESOURCE_EXHAUSTED"):
        self.failures = failures
        self.error_text = error_text
        self.calls = 0

    def generate_content(self, model, contents):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(self.error_text)
        return type("Response", (), {"text": "ok"})()


def use_fake_client(monkeypatch, models):
    monkeypatch.setattr(generate, "client", type("Client", (), {"models": models})())
    monkeypatch.setattr(generate.time, "sleep", lambda seconds: None)  # no real waiting in tests


def test_call_model_retries_after_a_rate_limit(monkeypatch):
    models = FakeModels(failures=2)
    use_fake_client(monkeypatch, models)

    assert generate.call_model("p", "m") == "ok"
    assert models.calls == 3


def test_call_model_gives_up_after_three_tries(monkeypatch):
    models = FakeModels(failures=5)
    use_fake_client(monkeypatch, models)

    try:
        generate.call_model("p", "m")
        assert False, "should have raised"
    except RuntimeError:
        pass
    assert models.calls == 3


def test_call_model_does_not_retry_other_errors(monkeypatch):
    models = FakeModels(failures=5, error_text="400 bad request")
    use_fake_client(monkeypatch, models)

    try:
        generate.call_model("p", "m")
    except RuntimeError:
        pass
    assert models.calls == 1
