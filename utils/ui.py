"""Small helpers shared by every Streamlit page: sidebar, error messages, labels.

Error details go to the terminal (the "log"). The screen only shows a short,
plain message, so passwords or file paths never appear in the browser.
"""
import logging

import pandas as pd
import psycopg
import streamlit as st

from core.db import fetch_all
from utils.theme import theme_toggle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rag")

# Database status words, as people should read them on screen.
STATUS_LABELS = {
    "indexed": "Ready",
    "quarantined": "Set aside",
    "pending": "Waiting",
    "validated": "Checked",
    "failed": "Failed",
}


# The page that "go to Upload" links point at.
UPLOAD_PAGE = "views/upload.py"

# Characters that Markdown treats as formatting (links, images, bold, lists...).
MARKDOWN_CHARACTERS = "\\`*_{}[]()#+-.!|<>~$:"


def when(moment) -> str:
    # One date format for every page, like "2026-11-08 14:05".
    return f"{moment:%Y-%m-%d %H:%M}"


def escape_markdown(text: str) -> str:
    """Put a backslash before every formatting character, so the text shows exactly as typed.

    Needed because anyone can upload files: a column named "[click](https://...)"
    must show as those characters, not as a link.
    """
    escaped = ""
    for character in text:
        if character in MARKDOWN_CHARACTERS:
            escaped += "\\"
        escaped += character
    return escaped


def show_table(rows) -> None:
    """A plain table for short lists. Unlike st.dataframe, it follows the light/dark look.

    st.table reads text as Markdown, so every text cell and heading is escaped first.
    """
    table = pd.DataFrame(rows)
    safe_columns = {}
    for column in table.columns:
        values = []
        for value in table[column]:
            if isinstance(value, str):
                values.append(escape_markdown(value))
            else:
                values.append(value)  # numbers stay numbers
        safe_columns[escape_markdown(str(column))] = values
    st.table(pd.DataFrame(safe_columns), hide_index=True)


def readable_documents(documents: list[dict]) -> list[dict]:
    """The same rows, with friendly status words and column names for tables."""
    rows = []
    for document in documents:
        rows.append({
            "File": document["filename"],
            "Group": document["source"],
            "Status": STATUS_LABELS.get(document["status"], document["status"]),
            "Passages": document["chunks"],
            "Added": when(document["ingested_at"]),
        })
    return rows


def friendly_message(error: Exception) -> str:
    """Turn a technical error into a short message a person can act on."""
    # Imported here, not at the top: loading core.generate needs the Gemini key, and
    # app.py must be able to show "missing settings" before the key is checked.
    from core.generate import is_rate_limit

    text = str(error)
    # Checked first: a query stopped for taking too long is a special kind of OperationalError.
    if isinstance(error, psycopg.errors.QueryCanceled):
        return "The database took too long to answer. Please try again in a moment."
    if isinstance(error, psycopg.OperationalError):
        return "Cannot reach the database. Check DATABASE_URL in your .env file and your internet connection."
    if is_rate_limit(error):
        return "Gemini is busy or the free limit was reached. Please wait a minute and try again."
    if "API key" in text or "API_KEY" in text or "403" in text:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."
    # Unknown error: say so plainly. The details are in the terminal log, not on screen.
    return "Something went wrong. The details were written to the terminal log."


def show_error(error: Exception) -> None:
    log.exception("page error")  # full details, for whoever runs the app
    st.error(friendly_message(error))


@st.cache_data(ttl=30)
def database_is_up() -> bool:
    # Remembered for 30 seconds, so the sidebar does not ask the database on every click.
    try:
        fetch_all("select 1")
        return True
    except Exception:
        log.exception("database check failed")
        return False


def show_sidebar() -> None:
    with st.sidebar:
        st.markdown("**Enterprise RAG Assistant**")
        st.caption("Answers from your own documents, with the sources to check them.")
        theme_toggle()
        st.divider()
        if database_is_up():
            st.caption(":green[●] Database connected")
        else:
            st.caption(":red[●] Database not reachable")
        st.caption(":green[●] Gemini key loaded")


def empty_state(message: str, page: str, label: str) -> None:
    # Shown when a page has nothing to display yet, with a link to the page that fixes it.
    st.info(message)
    st.page_link(page, label=label)
