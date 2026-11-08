import pandas as pd

from core.validate import mask_pii, validate_csv, validate_pages


def test_validate_csv_accepts_clean_frame():
    df = pd.DataFrame({"name": ["a", "b"], "amount": [1, 2]})
    assert validate_csv(df) == []  # no problems


def test_validate_csv_rejects_empty_frame():
    problems = validate_csv(pd.DataFrame(columns=["name"]))
    assert any("fewer than" in problem for problem in problems)


def test_validate_csv_rejects_mostly_empty_column():
    df = pd.DataFrame({"name": ["a", None, None], "amount": [1, 2, 3]})
    problems = validate_csv(df)
    assert any("'name'" in problem for problem in problems)


def test_validate_csv_rejects_duplicate_rows():
    df = pd.DataFrame({"name": ["a", "a"], "amount": [1, 1]})
    assert "duplicate rows" in validate_csv(df)


def test_validate_csv_rejects_duplicate_column_names():
    df = pd.DataFrame([[1, 2]], columns=["a", "a"])
    assert validate_csv(df) == ["duplicate column names"]


def test_validate_pages_rejects_short_text():
    assert validate_pages(["hi"]) != []


def test_validate_pages_accepts_enough_text():
    assert validate_pages(["x" * 300]) == []


def test_mask_pii_masks_email_and_phone():
    out = mask_pii("Contact a.b@example.com or +91 98765 43210 today")
    assert "[EMAIL]" in out
    assert "[PHONE]" in out
    assert "example.com" not in out
