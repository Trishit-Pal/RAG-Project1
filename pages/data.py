"""Page "Explore data": summaries, charts and filters for an uploaded CSV.

No AI is used on this page. The numbers come straight from pandas, so they are exact.
The CSV files come from data/uploads (saved by the Upload page).
"""
import pandas as pd
import streamlit as st

from core import dataview
from core.parse import parse_csv
from core.uploads import list_saved_csvs
from utils.ui import empty_state, show_error

MAX_SCATTER_POINTS = 5000  # more points than this makes the chart slow
MAX_FILTER_CHOICES = 50    # a column with more different values is not a good filter


@st.cache_resource(max_entries=5)
def load_csv(path: str, modified: float) -> pd.DataFrame:
    # `modified` is only here so the cache refreshes when the file changes.
    # cache_resource shares one copy instead of copying the table on every click.
    # That is safe because the dataview helpers never change the table they get.
    return parse_csv(path)


st.title("Explore data")

files = list_saved_csvs()
if not files:
    empty_state("No CSV files yet. Upload one first.", "pages/upload.py", "Go to Upload")
    st.stop()

# Show file names in the list, then look up the full path of the one picked.
files_by_name = {}
for path in files:
    files_by_name[path.name] = path
chosen_name = st.selectbox("Choose a CSV file", list(files_by_name))
chosen = files_by_name[chosen_name]
try:
    df = load_csv(str(chosen), chosen.stat().st_mtime)
except Exception as err:
    show_error(err)
    st.stop()

numbers, text_columns = dataview.column_kinds(df)

overview_tab, columns_tab, charts_tab, filter_tab = st.tabs(
    ["Overview", "Columns", "Charts", "Filter and download"]
)

with overview_tab:
    cells = st.columns(4)
    cells[0].metric("Rows", f"{len(df):,}")
    cells[1].metric("Columns", len(df.columns))
    cells[2].metric("Number columns", len(numbers))
    cells[3].metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
    st.subheader("First rows")
    st.dataframe(df.head(50), width="stretch")

with columns_tab:
    overview = dataview.column_overview(df)
    st.subheader("Missing values per column")
    st.bar_chart(overview.set_index("column")["missing_pct"], y_label="% missing")
    st.dataframe(overview, hide_index=True, width="stretch")
    if numbers:
        st.subheader("Summary of number columns")
        st.dataframe(df[numbers].describe().T, width="stretch")
    if text_columns:
        st.subheader("Most common values")
        picked = st.selectbox("Column", text_columns, key="common_column")
        st.bar_chart(df[picked].value_counts().head(15))

with charts_tab:
    DISTRIBUTION = "Distribution of a number"
    AVERAGE = "Average by group"
    TREND = "Trend over rows"
    COMPARE = "Compare two numbers"
    kind = st.radio("Chart type", [DISTRIBUTION, AVERAGE, TREND, COMPARE], horizontal=True)
    if not numbers:
        st.info("This file has no number columns, so there is nothing to chart.")
    elif kind == DISTRIBUTION:
        column = st.selectbox("Number column", numbers, key="hist_column")
        bins = st.slider("Number of bars", 5, 50, 20)
        counts = dataview.histogram_counts(df[column], bins)
        if counts.empty:
            st.info(f"'{column}' has no values to chart (every cell is empty).")
        else:
            st.bar_chart(counts, x_label=f"{column} (middle of each bucket)", y_label="rows")
    elif kind == AVERAGE:
        if not text_columns:
            st.info("This file has no text columns to group by.")
        else:
            group = st.selectbox("Group by", text_columns, key="group_column")
            value = st.selectbox("Average of", numbers, key="group_value")
            st.bar_chart(dataview.group_average(df, group, value), y_label=f"average {value}")
    elif kind == TREND:
        column = st.selectbox("Number column", numbers, key="line_column")
        st.line_chart(df[column])
    else:
        if len(numbers) < 2:
            st.info("You need at least two number columns for this chart.")
        else:
            x_axis = st.selectbox("Horizontal axis", numbers, key="scatter_x")
            y_axis = st.selectbox("Vertical axis", numbers, index=1, key="scatter_y")
            st.scatter_chart(df.head(MAX_SCATTER_POINTS), x=x_axis, y=y_axis)

with filter_tab:
    filtered = df
    filter_left, filter_right = st.columns(2)
    with filter_left:
        # Only columns with a short list of different values make good filters.
        categories = []
        for column in text_columns:
            if df[column].nunique() <= MAX_FILTER_CHOICES:
                categories.append(column)
        if categories:
            category = st.selectbox("Filter by category", categories)
            values = st.multiselect(
                "Keep only these values (leave empty to keep all)",
                sorted(df[category].dropna().unique()),
            )
            filtered = dataview.filter_by_values(filtered, category, values)
    with filter_right:
        if numbers:
            number = st.selectbox("Filter by number", numbers, key="filter_number")
            low, high = float(df[number].min()), float(df[number].max())
            if low < high:
                chosen_low, chosen_high = st.slider("Range", low, high, (low, high))
                filtered = dataview.filter_by_range(filtered, number, chosen_low, chosen_high)
    st.caption(f"{len(filtered):,} of {len(df):,} rows match")
    st.dataframe(filtered, width="stretch")
    st.download_button(
        "Download these rows as CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"filtered_{chosen.name}",
        mime="text/csv",
    )
