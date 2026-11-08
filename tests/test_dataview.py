import pandas as pd

from core import dataview


def sample() -> pd.DataFrame:
    return pd.DataFrame({
        "region": ["north", "south", "north", None],
        "sales": [10, 20, 30, 40],
    })


def test_column_overview_counts_missing_and_unique_values():
    overview = dataview.column_overview(sample()).set_index("column")

    assert overview.loc["region", "missing"] == 1
    assert overview.loc["region", "unique"] == 2
    assert overview.loc["sales", "missing_pct"] == 0.0


def test_column_kinds_splits_numbers_from_text():
    numbers, text = dataview.column_kinds(sample())
    assert numbers == ["sales"]
    assert text == ["region"]


def test_filter_by_values_keeps_only_the_chosen_ones():
    result = dataview.filter_by_values(sample(), "region", ["north"])
    assert list(result["sales"]) == [10, 30]


def test_filter_by_values_with_nothing_chosen_keeps_everything():
    assert len(dataview.filter_by_values(sample(), "region", [])) == 4


def test_filter_by_range_is_inclusive():
    result = dataview.filter_by_range(sample(), "sales", 20, 30)
    assert list(result["sales"]) == [20, 30]


def test_filter_does_not_change_the_original():
    df = sample()
    dataview.filter_by_values(df, "region", ["north"])
    assert len(df) == 4


def test_histogram_counts_adds_up_to_the_number_of_values():
    counts = dataview.histogram_counts(pd.Series([1, 2, 2, 3, 9]), bins=4)
    assert counts.sum() == 5


def test_histogram_counts_ignores_missing_values():
    counts = dataview.histogram_counts(pd.Series([1.0, None, 3.0]), bins=2)
    assert counts.sum() == 2


def test_histogram_labels_are_numbers_in_increasing_order():
    counts = dataview.histogram_counts(pd.Series(range(1, 101)), bins=5)
    labels = list(counts.index)
    assert all(isinstance(label, float) for label in labels)
    assert labels == sorted(labels)


def test_histogram_of_an_empty_column_returns_no_bars_instead_of_crashing():
    assert dataview.histogram_counts(pd.Series([None, None], dtype="float64")).empty


def test_histogram_labels_stay_distinct_for_tiny_ranges():
    counts = dataview.histogram_counts(pd.Series([0.0001 * i for i in range(100)]), bins=20)
    assert counts.index.is_unique


def test_full_range_keeps_rows_with_empty_cells():
    df = pd.DataFrame({"sales": [10, None, 30]})
    # The slider starts at the full range: that must not hide the empty row.
    assert len(dataview.filter_by_range(df, "sales", 10, 30)) == 3


def test_top_group_averages_keeps_only_the_highest_groups():
    df = pd.DataFrame({"name": ["a", "a", "b", "c", "d"], "score": [1, 3, 10, 5, 7]})
    result = dataview.top_group_averages(df, "name", "score", limit=2)
    assert list(result.index) == ["b", "d"]  # highest averages first
