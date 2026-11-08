"""Page "Upload": add files and live weather data to the searchable library.

The checking and saving happens in core/ingest.py. This file only shows the form.
"""
from pathlib import Path

import streamlit as st

from core.ingest import API_SOURCES, SUPPORTED_TYPES, ingest_api, ingest_file
from core.uploads import remove_upload, save_upload
from core.validate import MAX_NULL_RATIO, MAX_PAGES, MIN_TEXT_CHARS
from utils.ui import show_error

OUTCOME_LABELS = {
    "indexed": "✅ Added",
    "skipped": "⏭️ Already stored",
    "quarantined": "⚠️ Set aside",
    "rejected": "🚫 Not supported",
    "error": "❌ Problem",
}

st.title("Upload")
st.write("Files are checked first. Good files are stored and searchable. Files with problems are set aside, never stored.")

with st.expander("What gets checked?"):
    st.markdown(
        f"- **CSV:** at least one row, no duplicate rows or column names, no column more than {MAX_NULL_RATIO:.0%} empty.\n"
        f"- **PDF, Word, text:** at least {MIN_TEXT_CHARS} characters of readable text (scanned images fail), PDFs up to {MAX_PAGES} pages.\n"
        "- **Personal data:** email addresses and phone numbers are replaced with [EMAIL] and [PHONE] before storing.\n"
        f"- **Size:** up to {st.get_option('server.maxUploadSize')} MB per file."
    )

files_tab, api_tab = st.tabs(["Files", "Live weather data"])


def process_file(uploaded, group_name: str) -> tuple[str, str]:
    # Returns (outcome word, detail). Never raises, so one bad file does not stop the rest.
    try:
        path = save_upload(uploaded.name, uploaded.getvalue())
    except ValueError as err:  # a friendly message from save_upload; nothing was saved
        return "rejected", str(err)

    try:
        outcome, detail = ingest_file(str(path), group_name or Path(uploaded.name).stem)
    except Exception as err:
        show_error(err)
        outcome, detail = "error", uploaded.name

    # Files that were set aside or failed are not kept, so the Data page only shows good files.
    if outcome in ("quarantined", "error"):
        remove_upload(path)
    return outcome, detail


# The uploader wants extensions without the dot: "csv", not ".csv".
allowed_extensions = []
for extension in SUPPORTED_TYPES:
    allowed_extensions.append(extension.lstrip("."))

with files_tab:
    uploaded_files = st.file_uploader(
        "Choose files",
        type=allowed_extensions,
        accept_multiple_files=True,
        help="You can select several files at once.",
    )
    group_name = st.text_input(
        "Group name (optional)",
        help="Files with the same group name share one quality score. Leave empty to use each file's name.",
    )
    if uploaded_files:
        sizes = []
        for uploaded in uploaded_files:
            sizes.append(f"{uploaded.name} ({uploaded.size / 1024:,.0f} KB)")
        st.caption(", ".join(sizes))

    if st.button("Add to knowledge base", type="primary", disabled=not uploaded_files):
        rows = []
        added = 0
        progress = st.progress(0.0)
        done = 0
        for uploaded in uploaded_files:
            with st.status(f"Processing {uploaded.name}...", expanded=False) as status:
                outcome, detail = process_file(uploaded, group_name.strip())
                label = OUTCOME_LABELS.get(outcome, outcome)
                status.update(label=f"{uploaded.name}: {label}", state="complete")
            rows.append({"File": uploaded.name, "Result": label, "Details": detail})
            if outcome == "indexed":
                added += 1
            done += 1
            progress.progress(done / len(uploaded_files))
        st.dataframe(rows, hide_index=True, width="stretch")
        if added:
            st.success(f"{added} file(s) added. You can now ask questions about them.")

with api_tab:
    st.write("Fetch live data from a public API and store it like a CSV.")
    for name, config in API_SOURCES.items():
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(f"{config['url']} · Weather data by Open-Meteo.com (free for non-commercial use)")
            if st.button("Fetch latest data", key=f"api_{name}"):
                try:
                    with st.spinner("Fetching and storing..."):
                        outcome, detail = ingest_api(name)
                    st.info(f"{OUTCOME_LABELS.get(outcome, outcome)}: {detail}")
                except Exception as err:
                    show_error(err)
