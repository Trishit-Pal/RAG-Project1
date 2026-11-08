import pandas as pd
import pytest

from utils import charts, theme


@pytest.fixture(params=["light", "dark"])
def mode(request, monkeypatch):
    # Run each test once in light mode and once in dark mode.
    monkeypatch.setattr(theme, "is_dark", lambda: request.param == "dark")
    return theme.PALETTES[request.param]


def test_palette_follows_the_dark_mode_switch(monkeypatch):
    monkeypatch.setattr(theme, "is_dark", lambda: True)
    assert theme.palette() == theme.PALETTES["dark"]
    monkeypatch.setattr(theme, "is_dark", lambda: False)
    assert theme.palette() == theme.PALETTES["light"]


def test_both_modes_have_the_same_color_names():
    assert set(theme.PALETTES["light"]) == set(theme.PALETTES["dark"])


def test_bar_chart_uses_the_accent_for_the_current_mode(mode):
    df = pd.DataFrame({"name": ["a", "b"], "score": [0.9, 0.5]})
    spec = charts.bar_chart(df, "name", "score", "Group", "Score").to_dict()
    assert spec["mark"]["color"] == mode["accent"]
    assert spec["encoding"]["y"]["sort"] == "-x"  # longest bar first


def test_highlight_bars_color_used_sources_accent_and_others_gray(mode):
    df = pd.DataFrame({"source": ["[1]", "[2]"], "match": [0.8, 0.6], "status": ["Used", "Not used"]})
    spec = charts.highlight_bars(df, "source", "match", "status", "Match", "Used", "Not used").to_dict()
    scale = spec["layer"][0]["encoding"]["color"]["scale"]
    assert scale["domain"] == ["Used", "Not used"]
    assert scale["range"] == [mode["accent"], mode["gray"]]


def test_highlight_bars_never_draws_text_in_the_bar_color(mode):
    df = pd.DataFrame({"source": ["[1]"], "match": [0.8], "status": ["Used"]})
    spec = charts.highlight_bars(df, "source", "match", "status", "Match", "Used", "Not used").to_dict()
    assert spec["layer"][1]["mark"]["color"] == mode["muted"]


def test_split_bar_gives_ready_files_the_accent(mode):
    spec = charts.split_bar(ready=4, set_aside=1).to_dict()
    assert spec["encoding"]["color"]["scale"]["domain"] == ["Ready (4)", "Set aside (1)"]
    assert spec["encoding"]["color"]["scale"]["range"] == [mode["accent"], mode["gray"]]


def test_series_to_frame_makes_a_two_column_table_with_text_labels():
    counts = pd.Series([5, 2], index=[2024, 2025])
    frame = charts.series_to_frame(counts, "year", "rows")
    assert list(frame.columns) == ["year", "rows"]
    assert list(frame["year"]) == ["2024", "2025"]


def test_histogram_keeps_one_column_per_range_in_number_order(mode):
    counts = pd.Series([2, 5, 1], index=[1.5, 2.5, 3.5])
    spec = charts.histogram_chart(counts, "sales").to_dict()
    assert spec["encoding"]["x"]["field"] == "middle"
    assert spec["encoding"]["x"]["type"] == "ordinal"


def test_line_and_scatter_build_without_errors(mode):
    df = pd.DataFrame({"day": [1, 2, 3], "count": [4, 1, 3]})
    assert charts.line_chart(df, "day", "count", "Day", "Count").to_dict()["layer"]
    assert charts.scatter_chart(df, "day", "count", "Day", "Count").to_dict()["mark"]["type"] == "circle"


def test_line_chart_can_force_whole_numbers_on_the_axis(mode):
    df = pd.DataFrame({"day": [1, 2], "count": [1, 2]})
    spec = charts.line_chart(df, "day", "count", "Day", "Count", whole_numbers=True).to_dict()
    assert spec["layer"][0]["encoding"]["y"]["axis"]["tickMinStep"] == 1
