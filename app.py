"""Entry point. Run with:  streamlit run app.py

This file only sets up the page frame (title, .env check, sidebar) and lists
the pages. Each page lives in its own small file in the views/ folder.
The folder is not called "pages/": Streamlit would turn that name into a second,
automatic page list that skips this file (no theme, no settings check).
"""
import streamlit as st

# set_page_config must be the first Streamlit call.
st.set_page_config(
    page_title="Enterprise RAG Assistant",
    page_icon=":material/neurology:",
    layout="wide",
)

from core.config import missing_settings  # noqa: E402  (imports after set_page_config)
from utils.theme import apply_theme  # noqa: E402
from utils.ui import show_sidebar  # noqa: E402

apply_theme()  # light or dark look, chosen with the switch in the sidebar

missing = missing_settings()
if missing:
    st.error(f"Missing settings in your .env file: {', '.join(missing)}")
    st.stop()  # nothing below this line runs

show_sidebar()

navigation = st.navigation({
    "": [
        st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Explore": [
        st.Page("views/documents_qa.py", title="Ask your documents", icon=":material/chat:"),
        st.Page("views/data.py", title="Explore data", icon=":material/bar_chart:", url_path="explore-data"),
    ],
    "Manage": [
        st.Page("views/upload.py", title="Upload", icon=":material/upload_file:"),
        st.Page("views/quality.py", title="Data quality", icon=":material/verified:"),
        st.Page("views/evaluation.py", title="Evaluation", icon=":material/fact_check:"),
    ],
})
navigation.run()
