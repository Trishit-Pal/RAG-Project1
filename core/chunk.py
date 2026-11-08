"""Cut documents into small passages ("chunks") that can be searched one by one.

Used by core/ingest.py.
"""
import pandas as pd


def chunk_rows(df: pd.DataFrame) -> list[str]:
    """One chunk per table row, like "region: North | sales: 120"."""
    chunks = []
    for _, row in df.iterrows():
        pairs = []
        for column in df.columns:
            if pd.notna(row[column]):  # skip empty cells
                pairs.append(f"{column}: {row[column]}")
        chunks.append(" | ".join(pairs))
    return chunks


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    """Cut text into pieces of `size` characters.

    Each piece repeats the last `overlap` characters of the one before, so a
    sentence cut in half still appears whole in one of the two pieces.
    """
    if size <= overlap:
        raise ValueError("size must be greater than overlap")

    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        if start + size >= len(text):
            break  # this piece reached the end of the text
        start += size - overlap
    return chunks
