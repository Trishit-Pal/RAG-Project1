from pathlib import Path

import pandas as pd
import pymupdf4llm


def parse_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def parse_pdf(path: str | Path) -> list[str]:
    pages = pymupdf4llm.to_markdown(str(path), page_chunks=True)
    return [page["text"] for page in pages]