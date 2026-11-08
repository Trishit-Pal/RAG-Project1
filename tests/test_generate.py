from core import generate


def test_generate_text_reports_the_primary_model(monkeypatch):
    monkeypatch.setattr(generate, "_call_model", lambda prompt, model: "hi")
    assert generate.generate_text("p") == ("hi", generate.PRIMARY_MODEL)


def test_generate_text_falls_back_when_rate_limited(monkeypatch):
    def fake_call(prompt, model):
        if model == generate.PRIMARY_MODEL:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "from fallback"

    monkeypatch.setattr(generate, "_call_model", fake_call)
    assert generate.generate_text("p") == ("from fallback", generate.FALLBACK_MODEL)
