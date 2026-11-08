"""Small table helpers for the Explore data page.

Every function returns a new table and never changes the one it was given.
"""
import pandas as pd


def column_overview(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: its type, how many cells are empty, and how many different values."""
    types = []
    for dtype in df.dtypes:
        types.append(str(dtype))
    return pd.DataFrame({
        "column": df.columns,
        "type": types,
        "missing": df.isna().sum().to_numpy(),
        "missing_pct": (df.isna().mean() * 100).round(1).to_numpy(),
        "unique": df.nunique().to_numpy(),
    })


def column_kinds(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return (number columns, other columns). Charts need to know which is which."""
    numbers = df.select_dtypes(include="number").columns.tolist()
    others = []
    for column in df.columns:
        if column not in numbers:
            others.append(column)
    return numbers, others


def filter_by_values(df: pd.DataFrame, column: str, values: list) -> pd.DataFrame:
    # No values chosen means "do not filter".
    if not values:
        return df.copy()
    return df[df[column].isin(values)].copy()


def filter_by_range(df: pd.DataFrame, column: str, low: float, high: float) -> pd.DataFrame:
    # A range that covers every value means "do not filter". Filtering anyway
    # would also drop rows whose cell in this column is empty.
    if low <= df[column].min() and high >= df[column].max():
        return df.copy()
    return df[df[column].between(low, high)].copy()


def top_group_averages(df: pd.DataFrame, group_column: str, value_column: str, limit: int) -> pd.Series:
    """Average per group (for example sales per region), highest first, top `limit` groups only.

    A column like "customer id" can have thousands of groups; one bar each
    would make a chart too tall to draw.
    """
    averages = df.groupby(group_column)[value_column].mean()
    return averages.sort_values(ascending=False).head(limit)


def histogram_counts(values: pd.Series, bins: int = 20) -> pd.Series:
    """Count how many values fall into each of `bins` equal-width buckets.

    Empty cells are skipped. Each bucket is labelled with the number in its middle.
    """
    present = values.dropna()
    if present.empty:
        return pd.Series(dtype="int64")  # nothing to count (pd.cut would crash)

    counts = pd.cut(present, bins=bins).value_counts(sort=False)
    # Labels must be numbers, not text: the chart sorts text alphabetically,
    # which would scramble the order. 6 significant digits keeps them short but
    # still different from each other, even for tiny ranges like 0.0001.
    labels = []
    for bucket in counts.index:
        labels.append(float(f"{bucket.mid:.6g}"))
    counts.index = labels
    return counts
