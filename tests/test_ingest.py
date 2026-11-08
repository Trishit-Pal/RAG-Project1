from core.ingest import hourly_to_frame, sha256_bytes
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


def test_sha256_bytes_is_stable_and_different_for_different_input():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")


def test_hourly_to_frame_builds_one_row_per_time():
    data = {"hourly": {"time": ["t1", "t2"], "temperature_2m": [10.0, 11.0]}}
    df = hourly_to_frame(data)
    assert list(df.columns) == ["time", "temperature_2m"]
    assert len(df) == 2

def test_ingest_file_rejects_unknown_file_types(tmp_path):
    from core.ingest import ingest_file

    path = tmp_path / "photo.png"
    path.write_bytes(b"not really an image")

    outcome, detail = ingest_file(str(path), "src")
    assert outcome == "rejected"
    assert ".docx" in detail  # the message lists the supported types


def test_ingest_file_indexes_a_txt_file(tmp_path, monkeypatch):
    from core import ingest

    path = tmp_path / "notes.txt"
    path.write_text("word " * 100, encoding="utf-8")  # 500 characters, above the minimum
    seen = {}
    monkeypatch.setattr(ingest, "document_exists", lambda sha: False)
    monkeypatch.setattr(ingest, "get_or_create_source", lambda name, kind, uri=None: "source-1")
    monkeypatch.setattr(ingest, "index_texts", lambda *args: seen.update(texts=args[5]) or ("indexed", "ok"))

    result = ingest.ingest_file(str(path), "notes")

    assert result == ("indexed", "ok")
    assert len(seen["texts"]) >= 1


def test_ingest_file_quarantines_a_tiny_docx(tmp_path, monkeypatch):
    import docx

    from core import ingest

    path = tmp_path / "tiny.docx"
    document = docx.Document()
    document.add_paragraph("too short")
    document.save(str(path))
    monkeypatch.setattr(ingest, "document_exists", lambda sha: False)
    monkeypatch.setattr(ingest, "get_or_create_source", lambda name, kind, uri=None: "source-1")
    monkeypatch.setattr(ingest, "store_quarantined", lambda *args: None)

    assert ingest.ingest_file(str(path), "tiny")[0] == "quarantined"
