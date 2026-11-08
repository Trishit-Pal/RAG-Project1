import pandas as pd

from core.quality import score_pages, score_table


def test_score_table_clean_data_scores_one():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    assert score_table(df, passed=True)["score"] == 1.0


def test_score_table_penalises_nulls_and_duplicates():
    df = pd.DataFrame({"a": [1, 1, None], "b": ["x", "x", None]})
    assert score_table(df, passed=True)["score"] < 1.0


def test_score_pages_failed_validation_loses_validity_points():
    # completeness 1.0 * 0.5 + uniqueness 1.0 * 0.3 + validity 0.0 * 0.2 = 0.8
    assert score_pages(["hello"], passed=False)["score"] == 0.8

def test_score_table_reports_row_counts():
    df = pd.DataFrame({"a": [1, 2]})
    assert score_table(df, passed=True)["rows_in"] == 2
    assert score_table(df, passed=True)["rows_passed"] == 2
    # A file that failed validation passes zero rows.
    assert score_table(df, passed=False)["rows_passed"] == 0


def test_score_pages_reports_page_counts():
    result = score_pages(["a", "b", "c"], passed=True)
    assert result["rows_in"] == 3
    assert result["rows_passed"] == 3


class FakeConn:
    # Records every SQL call so the test can look at the values.
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))


def test_insert_quality_run_fills_the_required_columns():
    from core.quality import insert_quality_run

    conn = FakeConn()
    result = score_table(pd.DataFrame({"a": [1, 2]}), passed=True)

    insert_quality_run(conn, "source-1", result)

    sql, params = conn.calls[0]
    assert "rows_in" in sql and "rows_passed" in sql
    assert params[0] == "source-1"
    assert 2 in params  # rows_in
    # The second call keeps the latest score on the source row.
    assert conn.calls[1][1][1] == "source-1"
