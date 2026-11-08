import psycopg

from utils.ui import friendly_message


def test_database_errors_point_to_the_env_file():
    msg = friendly_message(psycopg.OperationalError("connection refused"))
    assert "database" in msg.lower()
    assert ".env" in msg


def test_rate_limit_errors_say_to_wait():
    msg = friendly_message(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert "wait" in msg.lower()


def test_unknown_errors_do_not_leak_details():
    msg = friendly_message(ValueError("password=hunter2 in /secret/path"))
    assert "hunter2" not in msg


def test_escape_markdown_turns_links_and_images_into_plain_text():
    from utils.ui import escape_markdown

    out = escape_markdown("![x](https://evil.example/p.png) [click](https://phish.example)")
    # Every character that starts an image or a link is now escaped.
    assert "\!\[x\]\(" in out
    assert "\[click\]\(" in out


def test_escape_markdown_leaves_ordinary_words_alone():
    from utils.ui import escape_markdown

    assert escape_markdown("Sales 2025") == "Sales 2025"


def test_show_table_escapes_text_cells_and_headings(monkeypatch):
    from utils import ui

    shown = {}
    monkeypatch.setattr(ui.st, "table", lambda data, hide_index: shown.update(data=data))

    ui.show_table([{"[evil](x)": "[click](https://phish.example)", "count": 3}])

    table = shown["data"]
    assert "\[evil\]\(x\)" in table.columns
    assert table.iloc[0, 0].startswith("\[click\]")
    assert table.iloc[0, 1] == 3  # numbers are left as numbers
