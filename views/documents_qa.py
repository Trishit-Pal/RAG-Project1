"""Page "Ask your documents": a chat that answers from your files, with sources.

The answering happens in core/ask.py. This file only shows the chat.
"""
import pandas as pd
import streamlit as st

from core.ask import NOT_FOUND, ask, cited_numbers, clear_answer_cache
from core.stats import count_indexed_documents, recent_questions
from utils.charts import highlight_bars, show
from utils.ui import UPLOAD_PAGE, empty_state, escape_markdown, show_error, when

st.title("Ask your documents")

try:
    ready = count_indexed_documents()
except Exception as err:
    show_error(err)
    st.stop()

if ready == 0:
    empty_state("Upload a document first, then come back to ask questions.", UPLOAD_PAGE, "Go to Upload")
    st.stop()

# The chat lives in session_state so it survives Streamlit re-running this file.
if "chat" not in st.session_state:
    st.session_state.chat = []


USED = "Used in the answer"
NOT_USED = "Not used"


def describe_sources(chunks: list[dict], answer: str) -> list[dict]:
    """One entry per source: its number, the passage, and whether the answer used it.

    Sources are numbered the same way as the [1], [2] markers in the answer.
    """
    cited = cited_numbers(answer)
    sources = []
    number = 1
    for chunk in chunks:
        if number in cited:
            status = USED
        else:
            status = NOT_USED
        sources.append({"number": number, "chunk": chunk, "status": status})
        number += 1
    return sources


def show_match_chart(sources: list[dict]) -> None:
    """A bar per source: how closely it matched the question, with used sources highlighted."""
    rows = []
    for source in sources:
        chunk = source["chunk"]
        if chunk["similarity"] is None:
            st.caption("Match scores are not kept for saved answers.")
            return
        rows.append({
            "source": f"[{source['number']}] {chunk['filename']}",
            "match": chunk["similarity"],
            "status": source["status"],
        })
    chart = highlight_bars(pd.DataFrame(rows), "source", "match", "status", "Match with your question", USED, NOT_USED)
    show(chart, "Bar chart of how closely each source matched the question, with the sources used in the answer highlighted")


def show_passages(sources: list[dict]) -> None:
    # One box per source; open it to read the passage.
    for source in sources:
        chunk = source["chunk"]
        # File names and passages come from uploads, so they are shown as plain text.
        name = escape_markdown(chunk["filename"])
        status = source["status"].lower()
        if chunk["similarity"] is None:  # saved answers do not keep the match score
            label = f"[{source['number']}] {name} ({status})"
        else:
            label = f"[{source['number']}] {name} ({chunk['similarity']:.0%} match, {status})"
        with st.expander(label):
            st.markdown(escape_markdown(chunk["text"]))


AVATARS = {"user": ":material/person:", "assistant": ":material/auto_awesome:"}


def show_message(message: dict) -> None:
    with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
        # Plain text: answers are written from documents anyone can upload.
        st.markdown(escape_markdown(message["text"]))
        if message["role"] != "assistant":
            return
        if message["text"] == NOT_FOUND:
            st.caption("Try different words, or upload a document that covers this topic.")
        if message["cached"]:
            caption = "Saved answer, reused"
        else:
            caption = "New answer"
        if message["model"]:
            caption += f", written by {message['model']}"
        st.caption(caption)
        if message["chunks"]:
            st.markdown("**Sources**")
            sources = describe_sources(message["chunks"], message["text"])
            show_match_chart(sources)
            show_passages(sources)


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
# A question typed on the Home page arrives here, ready to answer.
if not question and "pending_question" in st.session_state:
    question = st.session_state.pop("pending_question")
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
    # Questions from every visitor, so they are shown as plain text.
    for item in recent_questions(limit=10):
        st.markdown("**" + escape_markdown(item["question"]) + "**")
        st.caption(f"{when(item['created_at'])}, written by {item['model']}")
        st.markdown(escape_markdown(item["answer"]))
