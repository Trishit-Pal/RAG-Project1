"""Small Streamlit helpers shared by every page."""
import os

import streamlit as st
from dotenv import load_dotenv

from utils.logger import get_logger
from utils.messages import friendly_message

log = get_logger("ui")

REQUIRED_SETTINGS = ("DATABASE_URL", "GEMINI_API_KEY")

# Database status words, as people should read them on screen.
STATUS_LABELS = {
    "indexed": "Ready",
    "quarantined": "Set aside",
    "pending": "Waiting",
    "validated": "Checked",
    "failed": "Failed",
}


def when(moment) -> str:
    # One date format for every page.
    return f"{moment:%Y-%m-%d %H:%M}"


def readable_documents(documents: list[dict]) -> list[dict]:
    # Same rows, with friendly status words and column names for tables.
    return [
        {
            "File": d["filename"],
            "Group": d["source"],
            "Status": STATUS_LABELS.get(d["status"], d["status"]),
            "Passages": d["chunks"],
            "Added": when(d["ingested_at"]),
        }
        for d in documents
    ]


def missing_settings() -> list[str]:
    # Checked before anything else, so a missing key gives a clear message
    # instead of a crash deep inside the code.
    load_dotenv()
    return [name for name in REQUIRED_SETTINGS if not (os.getenv(name) or "").strip()]


@st.cache_data(ttl=30)
def database_is_up() -> bool:
    # Cached for 30 seconds so the sidebar does not hit the database on every click.
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
        db_up = database_is_up()
        st.markdown(f"{':green[●]' if db_up else ':red[●]'} Database")
        st.markdown(":green[●] Gemini key loaded")
        st.caption("Answers only use documents you uploaded. Nothing is guessed.")


def show_error(err: Exception) -> None:
    # Full details go to the terminal log. The screen gets a plain message.
    log.exception("page error")
    st.error(friendly_message(err))


def empty_state(message: str, page: str, label: str) -> None:
    st.info(message)
    st.page_link(page, label=label, icon=":material/arrow_forward:")
