"""Page "Data quality": how good the stored data is, and which files were set aside and why.

The scores are calculated in core/quality.py when a file is uploaded.
"""
import pandas as pd
import streamlit as st

from core.quality import WEIGHTS
from core.stats import list_documents, list_quality_runs, list_quarantine, list_sources
from utils.ui import readable_documents, show_error

st.title("Data quality")
MEANINGS = {
    "completeness": "how few cells or pages are empty",
    "uniqueness": "how few rows or pages are repeated",
    "validity": "whether the file passed the upload checks",
}
st.write("Every file gets a score from 0 (bad) to 1 (perfect), made of three parts:")
for name, weight in WEIGHTS.items():
    st.markdown(f"- **{name.capitalize()}** ({weight:.0%} of the score): {MEANINGS[name]}")

try:
    sources = list_sources()
    runs = list_quality_runs()
    quarantined = list_quarantine()
    documents = list_documents()
except Exception as err:
    show_error(err)
    st.stop()

# Only groups that already have a score.
scored = []
scores = []
for source in sources:
    if source["quality_score"] is not None:
        scored.append(source)
        scores.append(source["quality_score"])

summary_tab, runs_tab, quarantine_tab, documents_tab = st.tabs(
    ["Scores", "History", "Set-aside files", "All documents"]
)

with summary_tab:
    if not scored:
        st.info("No scores yet. Scores appear after you upload a file.")
    else:
        cells = st.columns(3)
        cells[0].metric("Average score", f"{sum(scores) / len(scores):.2f}")
        cells[1].metric("Groups scored", len(scores))
        cells[2].metric("Lowest score", f"{min(scores):.2f}")
        chart_data = pd.DataFrame(scored).set_index("name")["quality_score"]
        st.bar_chart(chart_data, y_label="score (1.0 is perfect)")
        st.caption("A low score usually means many empty cells or duplicate rows.")

with runs_tab:
    if runs:
        st.dataframe(
            runs,
            hide_index=True,
            width="stretch",
            column_config={
                "score": st.column_config.ProgressColumn("score", min_value=0.0, max_value=1.0, format="%.2f"),
                "completeness": st.column_config.NumberColumn(format="%.2f"),
                "duplicate_rate": st.column_config.NumberColumn(format="%.2f"),
            },
        )
    else:
        st.info("No quality checks have run yet.")

with quarantine_tab:
    if quarantined:
        st.warning(f"{len(quarantined)} problem(s) found. These files were not stored.")
        st.dataframe(quarantined, hide_index=True, width="stretch")
        st.caption("Fix the problem in the file, then upload it again.")
    else:
        st.success("No files have been set aside.")

with documents_tab:
    if documents:
        rows = readable_documents(documents)
        statuses = []
        for row in rows:
            if row["Status"] not in statuses:
                statuses.append(row["Status"])
        statuses = sorted(statuses)
        picked = st.multiselect("Show status", statuses, default=statuses)

        shown = []
        for row in rows:
            if row["Status"] in picked:
                shown.append(row)
        st.dataframe(shown, hide_index=True, width="stretch")
    else:
        st.info("No documents yet.")
