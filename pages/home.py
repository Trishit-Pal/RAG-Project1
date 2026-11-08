"""Page "Home": what the app does, what is stored, and a quick Gemini check."""
import streamlit as st

from core.generate import generate_text
from core.stats import list_documents, overview, recent_questions
from utils.ui import empty_state, readable_documents, show_error, when

st.title("Enterprise Document Intelligence")
st.write(
    "Upload your documents, then ask questions in plain English. "
    "Every answer shows the passages it came from, so you can check it."
)

try:
    info = overview()
    documents = list_documents(limit=10)
    questions = recent_questions(limit=5)
except Exception as err:
    show_error(err)
    st.stop()

indexed = info["documents"].get("indexed", 0)

columns = st.columns(4)
columns[0].metric("Documents ready", indexed)
columns[1].metric("Text passages stored", info["chunks"])
columns[2].metric("Questions answered", info["questions"])
columns[3].metric(
    "Files set aside",
    info["documents"].get("quarantined", 0),
    help="Files that failed the checks (for example, too many empty cells). See Data quality.",
)

if indexed == 0:
    empty_state(
        "Nothing is stored yet. Start by uploading a CSV, PDF, Word or text file.",
        "pages/upload.py",
        "Go to Upload",
    )

st.subheader("How it works")
steps = [
    ("1. Upload", "Add PDF, Word, text or CSV files."),
    ("2. Check", "Each file is checked for problems and given a quality score."),
    ("3. Search", "Your question is matched to the most similar passages."),
    ("4. Answer", "Gemini writes an answer using only those passages, with citations."),
]
step_columns = st.columns(4)
position = 0
for title, text in steps:
    with step_columns[position].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(text)
    position += 1

left, right = st.columns(2)
with left:
    st.subheader("Latest documents")
    if documents:
        st.dataframe(
            readable_documents(documents),
            hide_index=True,
            column_order=["File", "Status", "Passages", "Added"],
            width="stretch",
        )
    else:
        st.caption("No documents yet.")
with right:
    st.subheader("Latest questions")
    if questions:
        for item in questions:
            st.markdown(f"**{item['question']}**")
            st.caption(f"{when(item['created_at'])} · answered in {item['latency_ms'] / 1000:.1f} s")
    else:
        st.caption("No questions yet.")

with st.expander("System check"):
    st.write("Sends one short message to Gemini to confirm the key works.")
    if st.button("Test Gemini"):
        try:
            with st.spinner("Asking Gemini..."):
                reply, model = generate_text("Reply with the single word: ready")
            st.success(f"Gemini answered with {model}: {reply.strip()}")
        except Exception as err:
            show_error(err)
