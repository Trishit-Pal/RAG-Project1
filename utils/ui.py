"""Small helpers shared by every Streamlit page: sidebar, error messages, labels.

Error details go to the terminal (the "log"). The screen only shows a short,
plain message, so passwords or file paths never appear in the browser.
"""
import logging

import psycopg
import streamlit as st

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


def when(moment) -> str:
    # One date format for every page, like "2026-11-08 14:05".
    return f"{moment:%Y-%m-%d %H:%M}"


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
    text = str(error)
    if isinstance(error, psycopg.OperationalError):
        return "Cannot reach the database. Check DATABASE_URL in your .env file and your internet connection."
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
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
    from core.db import fetch_all

    try:
        fetch_all("select 1")
        return True
    except Exception:
        log.exception("database check failed")
        return False


def show_sidebar() -> None:
    with st.sidebar:
        st.subheader("System status")
        if database_is_up():
            st.markdown(":green[●] Database")
        else:
            st.markdown(":red[●] Database")
        st.markdown(":green[●] Gemini key loaded")
        st.caption("Answers only use documents you uploaded. Nothing is guessed.")


def empty_state(message: str, page: str, label: str) -> None:
    # Shown when a page has nothing to display yet, with a link to the page that fixes it.
    st.info(message)
    st.page_link(page, label=label, icon=":material/arrow_forward:")
