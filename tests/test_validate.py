import pandas as pd

from core.validate import mask_pii, validate_csv, validate_pages


def test_validate_csv_accepts_clean_frame():
    df = pd.DataFrame({"name": ["a", "b"], "amount": [1, 2]})
    assert validate_csv(df).ok


def test_validate_csv_rejects_empty_frame():
    result = validate_csv(pd.DataFrame(columns=["name"]))
    assert not result.ok
    assert any("fewer than" in r for r in result.reasons)


def test_validate_csv_rejects_mostly_null_column():
    df = pd.DataFrame({"name": ["a", None, None], "amount": [1, 2, 3]})
    result = validate_csv(df)
    assert not result.ok
    assert any("'name'" in r for r in result.reasons)


def test_validate_csv_rejects_duplicate_rows():
    df = pd.DataFrame({"name": ["a", "a"], "amount": [1, 1]})
    assert any("duplicate rows" in r for r in validate_csv(df).reasons)


def test_validate_pages_rejects_short_text():
    assert not validate_pages(["hi"]).ok


def test_validate_pages_accepts_enough_text():
    assert validate_pages(["x" * 300]).ok


def test_mask_pii_masks_email_and_phone():
    out = mask_pii("Contact a.b@example.com or +91 98765 43210 today")
    assert "[EMAIL]" in out
    assert "[PHONE]" in out
    assert "example.com" not in out