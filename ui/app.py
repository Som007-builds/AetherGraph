import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from agents.coordinator import run, format_report
from graph.queries import get_contradictions, get_gaps, get_all_claims

st.set_page_config(page_title="SciMesh", layout="wide")
st.title("SciMesh — AI Research Knowledge Graph")
st.caption("Multi-agent system for AI paper analysis | ArXiv 2023–2025")

# Sidebar stats
st.sidebar.header("Graph Stats")
try:
    claims = get_all_claims()
    contradictions = get_contradictions()
    gaps = get_gaps()
    st.sidebar.metric("Claims in graph", len(claims))
    st.sidebar.metric("Contradictions found", len(contradictions))
    st.sidebar.metric("Research gaps", len(gaps))
except Exception as e:
    st.sidebar.warning(f"DB not initialized: {e}")

tab1, tab2, tab3 = st.tabs(["Ask a Question", "Contradictions", "Research Gaps"])

with tab1:
    st.subheader("Ask the Coordinator")
    question = st.text_input(
        "Research question",
        placeholder="Does chain-of-thought prompting help small models?"
    )
    if st.button("Analyze") and question:
        with st.spinner("Coordinating agents..."):
            result = run(question)
            report = format_report(question, result)
        st.markdown(report)
        with st.expander("Raw JSON"):
            st.json(result)

with tab2:
    st.subheader("Detected Contradictions")
    contradictions = get_contradictions()
    if not contradictions:
        st.info("No contradictions yet. Run the contradiction detector first.")
    for c in contradictions[:20]:
        with st.expander(f"[{c['confidence']:.0%}] {c['explanation'][:80]}..."):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{c['paper_a'][:50]}**")
                st.write(c["claim_a"])
            with col2:
                st.write(f"**{c['paper_b'][:50]}**")
                st.write(c["claim_b"])

with tab3:
    st.subheader("Research Gaps")
    gaps = get_gaps()
    if not gaps:
        st.info("No gaps yet. Run the gap finder first.")
    for g in gaps[:20]:
        st.write(f"**→** {g['text']}")
        st.caption(f"Related to {len(g['related_claims'])} claims")
        st.divider()