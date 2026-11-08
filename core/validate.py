"""Check uploaded data before it is stored, and hide personal details.

Each check returns a list of problems. An empty list means the file is fine.
Used by core/ingest.py.
"""
import re

import pandas as pd

MIN_ROWS = 1
MAX_NULL_RATIO = 0.5    # a column may be at most half empty
MIN_TEXT_CHARS = 200    # less readable text than this usually means a scanned image
MAX_PAGES = 200

# Patterns that find email addresses and phone numbers in text.
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"\+?\d[\d -]{8,}\d")


def validate_csv(df: pd.DataFrame) -> list[str]:
    """Return the problems found in a table (an empty list means it is fine)."""
    if df.columns.duplicated().any():
        return ["duplicate column names"]

    problems = []
    if len(df) < MIN_ROWS:
        problems.append(f"fewer than {MIN_ROWS} row(s)")
    if df.duplicated().any():
        problems.append("duplicate rows")
    # isna().mean() gives, for each column, the share of empty cells.
    for column, empty_share in df.isna().mean().items():
        if empty_share > MAX_NULL_RATIO:
            problems.append(f"column '{column}' is {empty_share:.0%} empty (limit {MAX_NULL_RATIO:.0%})")
    return problems


def validate_pages(pages: list[str]) -> list[str]:
    """Check PDF, Word and text files, which all arrive as a list of text pages."""
    problems = []
    if not pages:
        problems.append("no pages")
    elif len(pages) > MAX_PAGES:
        problems.append(f"more than {MAX_PAGES} pages")

    total_characters = 0
    for page in pages:
        total_characters += len(page.strip())
    if total_characters < MIN_TEXT_CHARS:
        problems.append(f"less than {MIN_TEXT_CHARS} characters of readable text (scanned or empty file)")
    return problems


def mask_pii(text: str) -> str:
    # PII means "personally identifiable information": emails and phone numbers here.
    text = EMAIL_PATTERN.sub("[EMAIL]", text)
    return PHONE_PATTERN.sub("[PHONE]", text)
