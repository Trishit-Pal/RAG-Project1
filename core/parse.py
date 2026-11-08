"""Open each kind of file and get its text (or, for CSV, its table).

Used by core/ingest.py. PDF, Word and text readers all return a list of
"pages" of text, so the rest of the code can treat them the same way.
"""
from pathlib import Path

import docx
import pandas as pd
import pymupdf


def parse_csv(path: Path) -> pd.DataFrame:
    # low_memory=False reads the whole file before choosing column types, so a
    # column never ends up with a mix of numbers and text.
    return pd.read_csv(path, low_memory=False)


def parse_pdf(path: Path) -> list[str]:
    # One text per page. The "with" block closes the file when done.
    pages = []
    with pymupdf.open(str(path)) as document:
        for page in document:
            pages.append(page.get_text())
    return pages


def parse_docx(path: Path) -> list[str]:
    # A Word file has no pages, so the whole file is returned as one "page".
    document = docx.Document(str(path))
    lines = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            lines.append(paragraph.text)
    # Tables: one line per row, with " | " between the cells.
    for table in document.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                cells.append(cell.text.strip())
            lines.append(" | ".join(cells))
    return ["\n".join(lines)]


def parse_txt(path: Path) -> list[str]:
    raw = Path(path).read_bytes()
    # Windows Notepad's "Unicode" option saves UTF-16, which starts with these two bytes.
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16", errors="replace")
    else:
        # utf-8-sig also skips the optional UTF-8 marker. errors="replace" swaps
        # unreadable bytes for the "�" character instead of crashing.
        text = raw.decode("utf-8-sig", errors="replace")
    # Use plain "\n" line breaks (Windows writes "\r\n"), and remove NUL
    # characters, which the database refuses.
    return [text.replace("\r\n", "\n").replace("\x00", "")]
