"""Entry point. Run with:  streamlit run app.py

This file only sets up the page frame (title, .env check, sidebar) and lists
the pages. Each page lives in its own small file in the pages/ folder.
"""
import streamlit as st

# set_page_config must be the first Streamlit call.
st.set_page_config(
    page_title="Enterprise RAG Assistant",
    page_icon=":material/neurology:",
    layout="wide",
)

from utils.ui import missing_settings, show_sidebar  # noqa: E402

problems = missing_settings()
if problems:
    st.error(f"Missing settings in your .env file: {', '.join(problems)}")
    st.stop()  # nothing below this line runs

show_sidebar()

navigation = st.navigation({
    "": [
        st.Page("pages/home.py", title="Home", icon=":material/home:", default=True),
    ],
    "Explore": [
        st.Page("pages/documents_qa.py", title="Ask your documents", icon=":material/chat:"),
        st.Page("pages/data.py", title="Explore data", icon=":material/bar_chart:", url_path="explore-data"),
    ],
    "Manage": [
        st.Page("pages/upload.py", title="Upload", icon=":material/upload_file:"),
        st.Page("pages/quality.py", title="Data quality", icon=":material/verified:"),
        st.Page("pages/evaluation.py", title="Evaluation", icon=":material/fact_check:"),
    ],
})
navigation.run()
