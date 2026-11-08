import pandas as pd
import pytest

from core.chunk import chunk_rows, chunk_text


def test_chunk_rows_formats_each_row_as_pairs():
    df = pd.DataFrame({"name": ["Alice", "Bob"], "amount": [10, None]})

    chunks = chunk_rows(df)

    assert chunks == ["name: Alice | amount: 10.0", "name: Bob"]


def test_chunk_text_window_count_and_overlap():
    text = "".join(str(i % 10) for i in range(2500))

    chunks = chunk_text(text, size=1000, overlap=150)

    assert len(chunks) == 3
    assert all(len(c) <= 1000 for c in chunks)
    assert chunks[1][:150] == chunks[0][-150:]


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("   ") == []


def test_chunk_text_rejects_overlap_not_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("abc", size=100, overlap=100)