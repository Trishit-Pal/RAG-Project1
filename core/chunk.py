import pandas as pd


def chunk_rows(df: pd.DataFrame) -> list[str]:
    chunks = []
    for _, row in df.iterrows():
        pairs = [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
        chunks.append(" | ".join(pairs))
    return chunks


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    if size <= overlap:
        raise ValueError("size must be greater than overlap")

    text = text.strip()
    if not text:
        return []

    step = size - overlap
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        if start + size >= len(text):
            break
        start += step
    return chunks