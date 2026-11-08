"""Ask questions about the uploaded documents and see where each answer came from."""
import streamlit as st

from core.ask import NOT_FOUND, ask, cited_numbers, clear_answer_cache
from core.stats import count_indexed_documents, recent_questions
from utils.ui import empty_state, show_error, when

st.title("Ask your documents")

try:
    ready = count_indexed_documents()
except Exception as err:
    show_error(err)
    st.stop()

if ready == 0:
    empty_state("Upload a document first, then come back to ask questions.", "pages/upload.py", "Go to Upload")
    st.stop()

# The chat lives in session_state so it survives Streamlit re-running this file.
if "chat" not in st.session_state:
    st.session_state.chat = []


def show_sources(chunks: list[dict], answer: str) -> None:
    # Sources are numbered the same way as the [1], [2] markers in the answer.
    cited = cited_numbers(answer)
    for number, chunk in enumerate(chunks, start=1):
        match = "n/a" if chunk["similarity"] is None else f"{chunk['similarity']:.0%}"
        status = "used in the answer" if number in cited else "not used"
        with st.expander(f"[{number}] {chunk['filename']} · match {match} · {status}"):
            st.write(chunk["text"])


def show_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.write(message["text"])
        if message["role"] != "assistant":
            return
        if message["text"] == NOT_FOUND:
            st.caption("Try different words, or upload a document that covers this topic.")
        badge = "Saved answer, reused" if message["cached"] else "New answer"
        writer = f" · written by {message['model']}" if message["model"] else ""
        st.caption(badge + writer)
        if message["chunks"]:
            st.markdown("**Sources**")
            show_sources(message["chunks"], message["text"])


top_left, top_middle, top_right = st.columns([3, 1, 1])
top_left.caption("Answers use only your uploaded documents.")
if top_middle.button("New chat", icon=":material/add:"):
    st.session_state.chat = []
    st.rerun()
if top_right.button(
    "Forget saved answers",
    icon=":material/refresh:",
    help="Saved answers are reused for repeated questions. Click this to force fresh answers.",
):
    clear_answer_cache()
    st.toast("Saved answers cleared.")

for message in st.session_state.chat:
    show_message(message)

question = st.chat_input("Ask a question about your documents")
if question:
    st.session_state.chat.append({"role": "user", "text": question})
    show_message(st.session_state.chat[-1])
    try:
        with st.spinner("Searching your documents..."):
            result = ask(question)
    except Exception as err:
        show_error(err)
        st.stop()
    reply = {
        "role": "assistant",
        "text": result["answer"],
        "chunks": result["chunks"],
        "cached": result["cached"],
        "model": result["model"],
    }
    st.session_state.chat.append(reply)
    show_message(reply)

with st.expander("Earlier questions"):
    for item in recent_questions(limit=10):
        st.markdown(f"**{item['question']}**")
        st.caption(f"{when(item['created_at'])} · written by {item['model']}")
        st.write(item["answer"])
