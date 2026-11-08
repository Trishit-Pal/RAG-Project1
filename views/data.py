"""Page "Explore data": summaries, charts and filters for an uploaded CSV.

No AI is used on this page. The numbers come straight from pandas, so they are exact.
The CSV files come from data/uploads (saved by the Upload page).
"""
import pandas as pd
import streamlit as st

from core import dataview
from core.parse import parse_csv
from core.uploads import list_saved_csvs
from utils.charts import bar_chart, histogram_chart, line_chart, scatter_chart, show
from utils.ui import empty_state, show_error, show_table

MAX_CHART_POINTS = 5000  # the chart library refuses more rows than this, and it gets slow
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
    empty_state("No CSV files yet. Upload one first.", "views/upload.py", "Go to Upload")
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
    show(bar_chart(overview, "column", "missing_pct", "Column", "% of cells empty"),
         "Bar chart of the share of empty cells in each column")
    show_table(overview)
    if numbers:
        st.subheader("Summary of number columns")
        # describe() gives count, average, spread, smallest, quartiles and largest per column.
        # reset_index() turns the column names into a normal "column" column, so they show.
        summary = df[numbers].describe().T.round(2).reset_index().rename(columns={"index": "column"})
        show_table(summary)
    if text_columns:
        st.subheader("Most common values")
        picked = st.selectbox("Column", text_columns, key="common_column")
        counts = df[picked].value_counts().head(15)
        # Simple column names for the chart; the real name goes in the axis title.
        common = pd.DataFrame({"value": counts.index.astype(str), "rows": counts.to_numpy()})
        show(bar_chart(common, "value", "rows", picked, "rows"), f"Bar chart of the most common values in {picked}")

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
            show(histogram_chart(counts, column), f"Column chart of how {column} values are spread")
    elif kind == AVERAGE:
        if not text_columns:
            st.info("This file has no text columns to group by.")
        else:
            group = st.selectbox("Group by", text_columns, key="group_column")
            value = st.selectbox("Average of", numbers, key="group_value")
            averages = dataview.group_average(df, group, value)
            frame = pd.DataFrame({"group": averages.index.astype(str), "average": averages.to_numpy()})
            show(bar_chart(frame, "group", "average", group, f"average {value}"),
                 f"Bar chart of average {value} for each {group}")
    elif kind == TREND:
        column = st.selectbox("Number column", numbers, key="line_column")
        shown = df[column].head(MAX_CHART_POINTS)
        frame = pd.DataFrame({"row": range(1, len(shown) + 1), "value": shown.to_numpy()})
        show(line_chart(frame, "row", "value", "Row", column), f"Line chart of {column} row by row")
        if len(df) > MAX_CHART_POINTS:
            st.caption(f"Showing the first {MAX_CHART_POINTS:,} rows.")
    else:
        if len(numbers) < 2:
            st.info("You need at least two number columns for this chart.")
        else:
            x_axis = st.selectbox("Horizontal axis", numbers, key="scatter_x")
            y_axis = st.selectbox("Vertical axis", numbers, index=1, key="scatter_y")
            shown = df.head(MAX_CHART_POINTS)
            frame = pd.DataFrame({"x": shown[x_axis].to_numpy(), "y": shown[y_axis].to_numpy()})
            show(scatter_chart(frame, "x", "y", x_axis, y_axis), f"Scatter chart of {y_axis} against {x_axis}")
            if len(df) > MAX_CHART_POINTS:
                st.caption(f"Showing the first {MAX_CHART_POINTS:,} rows.")

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
