"""Page "Evaluation": check that search still finds the right documents.

Save a few questions and say which source should answer each one.
"Run evaluation" then checks whether search finds that source (see core/evals.py).
"""
import streamlit as st

from core.evals import PASS_HIT_RATE, TOP_K, add_case, delete_case, list_cases, list_runs, run_eval
from core.stats import list_sources
from utils.ui import empty_state, show_error, when

st.title("Evaluation")
st.write(
    f"A question is a **hit** when one of the top {TOP_K} passages comes from the source you expect. "
    f"The run passes at {PASS_HIT_RATE:.0%} hits or more. This tests search only, so it does not use up your Gemini answer quota."
)

try:
    sources = list_sources()
    cases = list_cases()
except Exception as err:
    show_error(err)
    st.stop()

if not sources:
    empty_state("Upload something first, so there is a source to test against.", "pages/upload.py", "Go to Upload")
    st.stop()

# source id -> source name, to show names instead of long ids.
source_names = {}
for source in sources:
    source_names[source["id"]] = source["name"]

cases_tab, run_tab = st.tabs(["Test questions", "Run and results"])

with cases_tab:
    with st.form("new_case", clear_on_submit=True):
        question = st.text_input("Test question")
        expected = st.multiselect(
            "Which source(s) should answer it?",
            list(source_names),
            format_func=source_names.get,
        )
        reference = st.text_area("Expected answer (optional, for your own notes)")
        if st.form_submit_button("Save test question"):
            if not question.strip() or not expected:
                st.warning("Enter a question and pick at least one source.")
            else:
                add_case(question, expected, reference.strip() or None)
                st.rerun()

    st.subheader(f"Saved questions ({len(cases)})")
    for case in cases:
        label = ", ".join(source_names.get(i, "removed source") for i in case["expected_source_ids"])
        with st.container(border=True):
            left, right = st.columns([5, 1])
            left.markdown(f"**{case['question']}**")
            left.caption(f"Expected source: {label}")
            if case["reference_answer"]:
                left.caption(f"Your note: {case['reference_answer']}")
            if right.button("Delete", key=f"delete_{case['id']}"):
                delete_case(case["id"])
                st.rerun()

with run_tab:
    if st.button("Run evaluation", type="primary", disabled=not cases):
        try:
            with st.spinner("Searching for each test question..."):
                outcome = run_eval()
        except Exception as err:
            show_error(err)
            st.stop()
        metrics = outcome["metrics"]
        message = f"{metrics['hits']} of {metrics['cases']} questions found the right source ({metrics['hit_rate']:.0%})."
        if outcome["passed"]:
            st.success("Passed. " + message)
        else:
            st.error("Failed. " + message)
        result_rows = []
        for result in outcome["results"]:
            result_rows.append({"Question": result["question"], "Result": "✅ hit" if result["hit"] else "❌ miss"})
        st.dataframe(result_rows, hide_index=True, width="stretch")

    st.subheader("Past runs")
    runs = list_runs()
    if runs:
        run_rows = []
        for run in runs:
            run_rows.append({
                "When": when(run["run_at"]),
                "App version": run["git_sha"],
                "Hit rate": f"{run['metrics'].get('hit_rate', 0):.0%}",
                "Result": "passed" if run["passed"] else "failed",
            })
        st.dataframe(run_rows, hide_index=True, width="stretch")
    else:
        st.caption("No runs yet.")
