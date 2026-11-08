"""Page "Home": what the app does, what is in the library, and a quick way to start.

A question typed here is handed to the "Ask your documents" page, which answers it.
"""
import pandas as pd
import streamlit as st

from core.generate import generate_text
from core.stats import list_documents, list_sources, overview, questions_per_day
from utils.charts import bar_chart, line_chart, show, split_bar
from utils.ui import UPLOAD_PAGE, empty_state, readable_documents, show_error, show_table

st.title("Ask your documents.")
st.write("Cited answers from your own files. Upload PDFs, Word or text files and CSVs, then ask in plain English.")

try:
    info = overview()
    documents = list_documents(limit=5)
    sources = list_sources()
    daily = questions_per_day()
except Exception as err:
    show_error(err)
    st.stop()

ready = info["documents"].get("indexed", 0)
set_aside = info["documents"].get("quarantined", 0)

# ---------- Ask straight away ----------
if ready == 0:
    empty_state("The library is empty. Upload a file first, then ask about it.", UPLOAD_PAGE, "Go to Upload")
else:
    with st.form("home_question", border=False):
        question_column, button_column = st.columns([5, 1], vertical_alignment="bottom")
        question = question_column.text_input("Your question", placeholder="What does the leave policy say about carry-over?")
        if button_column.form_submit_button("Ask", type="primary", width="stretch") and question.strip():
            # The Ask page picks this up and answers it.
            st.session_state["pending_question"] = question.strip()
            st.switch_page("views/documents_qa.py")

# ---------- Key numbers ----------
# One pass over the groups: their scores (for the average) and rows for the chart.
scores = []
scored = []
for source in sources:
    if source["quality_score"] is not None:
        scores.append(source["quality_score"])
        scored.append({"group": source["name"], "score": source["quality_score"]})

numbers = st.columns(3)
numbers[0].metric("Documents ready", ready)
numbers[1].metric("Passages stored", f"{info['chunks']:,}", help="Documents are cut into short passages. Search looks at these.")
if scores:
    numbers[2].metric("Average quality", f"{sum(scores) / len(scores):.2f}", help="0 is poor, 1 is perfect. See Data quality.")
else:
    numbers[2].metric("Average quality", "None yet")

# ---------- How it works (a real sequence, so it is numbered) ----------
st.subheader("How it works")
steps = [
    ("1. Upload", "Add PDF, Word, text or CSV files. Each file is checked, and files with problems are set aside."),
    ("2. Search", "Your question is matched to the passages with the closest meaning."),
    ("3. Answer", "Gemini answers using only those passages, and numbers each source so you can check it."),
]
step_columns = st.columns(3)
position = 0
for title, text in steps:
    with step_columns[position].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(text)
    position += 1

# ---------- What is in the library ----------
st.subheader("What is in the library")
left, right = st.columns(2, gap="large")

with left:
    st.markdown("**Files**")
    if ready + set_aside == 0:
        st.caption("No files yet.")
    elif set_aside == 0:
        # Nothing to compare, so a sentence says it better than a chart.
        st.write(f"All {ready} files passed the checks. None were set aside.")
    else:
        show(split_bar(ready, set_aside), f"{ready} files ready and {set_aside} set aside")

    st.markdown("**Quality by group**")
    if scored:
        show(bar_chart(pd.DataFrame(scored), "group", "score", "Group", "Score (1 is perfect)"),
             "Bar chart of the quality score of each group of files")
    else:
        st.caption("Scores appear after the first upload.")

with right:
    st.markdown("**Questions asked per day**")
    if daily:
        show(line_chart(pd.DataFrame(daily), "day", "questions", "Day", "Questions", x_type="T", whole_numbers=True),
             "Line chart of how many questions were asked each day over the last 30 days")
    else:
        st.caption("No questions in the last 30 days.")

# ---------- Latest files ----------
if documents:
    st.subheader("Latest files")
    show_table(readable_documents(documents))

with st.expander("Check the Gemini connection"):
    st.write("Sends one short message to Gemini to confirm the key works.")
    if st.button("Test Gemini"):
        try:
            with st.spinner("Asking Gemini..."):
                reply, model = generate_text("Reply with the single word: ready")
            st.success(f"Gemini answered with {model}: {reply.strip()}")
        except Exception as err:
            show_error(err)
