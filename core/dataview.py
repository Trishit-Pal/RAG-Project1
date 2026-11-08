"""Small pandas helpers for the Data page.

Every function returns a new table and never changes the one it was given.
"""
import pandas as pd


def column_overview(df: pd.DataFrame) -> pd.DataFrame:
    # One row per column: its type, how much is missing, and how many different values.
    return pd.DataFrame({
        "column": df.columns,
        "type": [str(t) for t in df.dtypes],
        "missing": df.isna().sum().to_numpy(),
        "missing_pct": (df.isna().mean() * 100).round(1).to_numpy(),
        "unique": df.nunique().to_numpy(),
    })


def column_kinds(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    # Returns (number columns, everything else). Charts need to know which is which.
    numbers = df.select_dtypes(include="number").columns.tolist()
    text = [c for c in df.columns if c not in numbers]
    return numbers, text


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


def group_average(df: pd.DataFrame, group_column: str, value_column: str) -> pd.Series:
    # For example: average sales per region.
    return df.groupby(group_column)[value_column].mean()


def histogram_counts(values: pd.Series, bins: int = 20) -> pd.Series:
    # How many values fall into each of `bins` equal-width buckets.
    # Missing values are skipped. Each bucket is labelled with its middle value.
    # Labels must be numbers: the chart sorts text labels alphabetically, which scrambles the order.
    present = values.dropna()
    if present.empty:
        return pd.Series(dtype="int64")  # nothing to count (pd.cut would crash)
    counts = pd.cut(present, bins=bins).value_counts(sort=False)
    # 6 significant figures keeps labels short but distinct, even for tiny ranges like 0.0001.
    counts.index = [float(f"{interval.mid:.6g}") for interval in counts.index]
    return counts

