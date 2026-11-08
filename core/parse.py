from pathlib import Path

import docx
import pandas as pd
import pymupdf


def parse_csv(path: str | Path) -> pd.DataFrame:
    # low_memory=False reads the whole file before choosing column types, so a
    # column never ends up with a mix of numbers and text.
    return pd.read_csv(path, low_memory=False)


def parse_pdf(path: str | Path) -> list[str]:
    # One text per page. The "with" block closes the file when done.
    pages = []
    with pymupdf.open(str(path)) as document:
        for page in document:
            pages.append(page.get_text())
    return pages


def parse_docx(path: str | Path) -> list[str]:
    # A Word file has no pages, so the whole file is returned as one "page".
    document = docx.Document(str(path))
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return ["\n".join(lines)]


def parse_txt(path: str | Path) -> list[str]:
    raw = Path(path).read_bytes()
    # Windows Notepad's "Unicode" option saves UTF-16, which starts with a byte-order mark.
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16", errors="replace")
    else:
        # utf-8-sig also drops the optional UTF-8 marker. errors="replace" swaps
        # unreadable bytes for the "�" character instead of crashing.
        text = raw.decode("utf-8-sig", errors="replace")
    # Use plain "\n" line breaks (Windows writes "\r\n"), and remove NUL
    # characters, which the database refuses.
    return [text.replace("\r\n", "\n").replace("\x00", "")]
