import re
from dataclasses import dataclass, field

import pandas as pd

MIN_ROWS = 1
MAX_NULL_RATIO = 0.5
MIN_TEXT_CHARS = 200
MAX_PAGES = 200

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d -]{8,}\d")


@dataclass
class ValidationResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def validate_csv(df: pd.DataFrame) -> ValidationResult:
    if df.columns.duplicated().any():
        return ValidationResult(False, ["duplicate column names"])

    reasons = []
    if len(df) < MIN_ROWS:
        reasons.append(f"fewer than {MIN_ROWS} row(s)")
    if df.duplicated().any():
        reasons.append("duplicate rows")
    for col, ratio in df.isna().mean().items():
        if ratio > MAX_NULL_RATIO:
            reasons.append(f"column '{col}' null ratio {ratio:.2f} above {MAX_NULL_RATIO}")
    return ValidationResult(ok=not reasons, reasons=reasons)


def validate_pages(pages: list[str]) -> ValidationResult:
    # Used for PDF, Word and text files: all of them become a list of text pages.
    reasons = []
    if not pages:
        reasons.append("no pages")
    elif len(pages) > MAX_PAGES:
        reasons.append(f"more than {MAX_PAGES} pages")
    if sum(len(p.strip()) for p in pages) < MIN_TEXT_CHARS:
        reasons.append(f"less than {MIN_TEXT_CHARS} characters of readable text (scanned or empty file)")
    return ValidationResult(ok=not reasons, reasons=reasons)


def mask_pii(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL]", text)
    return PHONE_RE.sub("[PHONE]", text)