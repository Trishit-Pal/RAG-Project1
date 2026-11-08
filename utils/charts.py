"""Charts that match the light or dark look.

Every page draws its charts with these functions, so they all look the same.
They use Altair, the chart library that comes with Streamlit.

Design rules followed here (from a data-visualization checklist):
- one strong color (the accent); gray for anything not highlighted
- text is never drawn in the bar color, only in text colors
- thin bars with rounded ends, faint gridlines, a tooltip on every chart
"""
import altair as alt
import pandas as pd
import streamlit as st

from utils.theme import palette

BAR_ROW_HEIGHT = 30  # pixels per row in horizontal bar charts (bar plus the gap around it)
BAR_GAP = 0.35       # share of each row left empty, so neighbouring bars never touch


def show(chart: alt.Chart, description: str) -> None:
    """Draw a chart on the page, colored for the current mode.

    description is read out by screen readers instead of the picture.
    """
    colors = palette()
    finished = (
        chart.configure(background="transparent", font="Instrument Sans")
        .configure_view(stroke=None)  # no box around the chart
        .configure_axis(
            labelColor=colors["muted"],
            titleColor=colors["muted"],
            gridColor=colors["grid"],
            domainColor=colors["line"],
            tickColor=colors["line"],
            labelFontSize=12,
            titleFontSize=12,
            titleFontWeight=500,
        )
        .configure_legend(labelColor=colors["ink"], titleColor=colors["muted"], orient="bottom")
    )
    # theme=None: use our colors, not Streamlit's built-in chart colors.
    st.altair_chart(finished, width="stretch", theme=None, alt=description)


def bar_chart(df: pd.DataFrame, label: str, value: str, label_title: str, value_title: str) -> alt.Chart:
    """Horizontal bars, longest first. Good for comparing named things."""
    return alt.Chart(df).mark_bar(color=palette()["accent"], cornerRadiusEnd=4).encode(
        x=alt.X(f"{value}:Q", title=value_title),
        y=alt.Y(f"{label}:N", title=label_title, sort="-x", scale=alt.Scale(paddingInner=BAR_GAP)),
        tooltip=[alt.Tooltip(f"{label}:N", title=label_title), alt.Tooltip(f"{value}:Q", title=value_title, format=",.2f")],
    ).properties(height=alt.Step(BAR_ROW_HEIGHT))  # each row gets the same height, however many there are


def histogram_chart(counts: pd.Series, value_title: str) -> alt.Chart:
    """Columns showing how many rows fall into each range of values.

    counts comes from core.dataview.histogram_counts (index = middle of each range).
    """
    df = pd.DataFrame({"middle": counts.index, "rows": counts.to_numpy()})
    # ":O" (ordered) puts one column per range, side by side, in number order.
    return alt.Chart(df).mark_bar(color=palette()["accent"], cornerRadiusEnd=4).encode(
        x=alt.X("middle:O", title=f"{value_title} (middle of each range)", axis=alt.Axis(format=",.4g", labelAngle=-45),
                scale=alt.Scale(paddingInner=0.1)),  # a thin gap so neighbouring columns stay apart
        y=alt.Y("rows:Q", title="rows"),
        tooltip=[alt.Tooltip("middle:Q", title=value_title, format=",.4g"), alt.Tooltip("rows:Q", title="rows")],
    ).properties(height=280)


def line_chart(df: pd.DataFrame, x: str, y: str, x_title: str, y_title: str, x_type: str = "Q",
               whole_numbers: bool = False) -> alt.Chart:
    """A line with a dot on each point (hover a dot to see its value).

    x_type: "Q" for numbers, "T" for dates.
    whole_numbers: True for counts, so the axis never shows 0.5 of something.
    """
    colors = palette()
    if whole_numbers:
        y_axis = alt.Axis(tickMinStep=1, format="d")
    else:
        y_axis = alt.Axis()
    base = alt.Chart(df).encode(
        x=alt.X(f"{x}:{x_type}", title=x_title),
        y=alt.Y(f"{y}:Q", title=y_title, axis=y_axis),
        tooltip=[alt.Tooltip(f"{x}:{x_type}", title=x_title), alt.Tooltip(f"{y}:Q", title=y_title)],
    )
    line = base.mark_line(color=colors["accent"], strokeWidth=2)
    # A ring in the background color keeps dots readable where they touch the line.
    dots = base.mark_point(filled=True, size=50, color=colors["accent"], stroke=colors["surface"], strokeWidth=2)
    return (line + dots).properties(height=280)


def scatter_chart(df: pd.DataFrame, x: str, y: str, x_title: str, y_title: str) -> alt.Chart:
    """One dot per row, to see whether two numbers move together."""
    colors = palette()
    return alt.Chart(df).mark_circle(size=60, color=colors["accent"], opacity=0.7, stroke=colors["surface"], strokeWidth=1).encode(
        x=alt.X(f"{x}:Q", title=x_title),
        y=alt.Y(f"{y}:Q", title=y_title),
        tooltip=[alt.Tooltip(f"{x}:Q", title=x_title), alt.Tooltip(f"{y}:Q", title=y_title)],
    ).properties(height=320)


def series_to_frame(series: pd.Series, label: str, value: str) -> pd.DataFrame:
    """Turn a list of numbers with names (a pandas Series) into a two-column table for a chart.

    The names become text, so the chart treats them as names, not as numbers.
    """
    return pd.DataFrame({label: series.index.astype(str), value: series.to_numpy()})


def split_bar(ready: int, set_aside: int) -> alt.Chart:
    """One bar split into two parts: files that are ready (accent) and set aside (gray)."""
    colors = palette()
    ready_label = f"Ready ({ready})"
    set_aside_label = f"Set aside ({set_aside})"
    rows = pd.DataFrame([
        {"label": ready_label, "count": ready, "position": 0},
        {"label": set_aside_label, "count": set_aside, "position": 1},
    ])
    # The 2px line in the background color between the parts keeps them apart.
    return alt.Chart(rows).mark_bar(cornerRadius=4, height=28, stroke=colors["page"], strokeWidth=2).encode(
        x=alt.X("count:Q", stack="zero", axis=None),
        color=alt.Color("label:N", title=None,
                        scale=alt.Scale(domain=[ready_label, set_aside_label], range=[colors["accent"], colors["gray"]])),
        order=alt.Order("position:Q"),  # "Ready" first
        tooltip=[alt.Tooltip("label:N", title="Status"), alt.Tooltip("count:Q", title="Files")],
    ).properties(height=90)  # room for the bar and the legend under it


def highlight_bars(df: pd.DataFrame, label: str, value: str, group: str, value_title: str,
                   on_text: str, off_text: str) -> alt.Chart:
    """Horizontal bars where some are highlighted (accent) and the rest are gray.

    group: the column saying which kind each bar is, holding either on_text or
    off_text. Those words also go in the legend, so the meaning never depends
    on color alone.
    """
    colors = palette()
    base = alt.Chart(df).encode(
        # sort=None keeps the given order: [1], [2], ...
        y=alt.Y(f"{label}:N", title=None, sort=None, scale=alt.Scale(paddingInner=BAR_GAP)),
        x=alt.X(f"{value}:Q", title=value_title, axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        tooltip=[alt.Tooltip(f"{label}:N", title="Source"), alt.Tooltip(f"{value}:Q", title=value_title, format=".0%"),
                 alt.Tooltip(f"{group}:N", title=" ")],
    )
    bars = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color(f"{group}:N", title=None,
                        scale=alt.Scale(domain=[on_text, off_text], range=[colors["accent"], colors["gray"]])),
    )
    # The value at the tip of each bar, in a text color (never the bar color).
    tips = base.mark_text(align="left", dx=6, color=colors["muted"], fontSize=12).encode(text=alt.Text(f"{value}:Q", format=".0%"))
    return (bars + tips).properties(height=alt.Step(BAR_ROW_HEIGHT))
