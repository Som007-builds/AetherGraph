import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from agents.coordinator_v2 import run as run_coordinator
from agents.coordinator import run as run_v1, format_report as fmt_v1
from graph.queries import get_contradictions, get_gaps, get_all_claims

st.set_page_config(page_title="SciMesh", layout="wide")
st.title("SciMesh - AI Research Knowledge Graph")
st.caption("Multi-agent system for AI paper analysis | ArXiv 2023-2025")

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

tab1, tab2, tab3, tab4 = st.tabs(["Ask a Question", "Contradictions", "Research Gaps", "Knowledge Graph"])

with tab1:
    st.subheader("Ask the Coordinator")

    col_q, col_mode = st.columns([4, 1])
    with col_q:
        question = st.text_input(
            "Research question",
            placeholder="Does chain-of-thought prompting help small models?"
        )
    with col_mode:
        use_v2 = st.toggle("Multi-step", value=True, help="v2: plan > retrieve > reflect > synthesize")

    if st.button("Analyze", type="primary") and question:
        with st.spinner("Coordinating agents..."):
            if use_v2:
                output = run_coordinator(question, verbose=False)
            else:
                raw = run_v1(question)
                output = {
                    "report": fmt_v1(question, raw),
                    "raw": raw,
                    "iterations": 1,
                    "reflection_log": [],
                    "plan": None
                }

        st.markdown(output["report"])

        if output.get("plan") and use_v2:
            with st.expander("Coordinator reasoning trace"):
                plan = output["plan"]
                st.write(f"**Planner strategy:** {plan.get('reasoning', '')}")
                st.write(f"**Sub-queries:** {', '.join(plan.get('sub_queries', []))}")

                for entry in output.get("reflection_log", []):
                    st.divider()
                    st.write(f"**Iteration {entry['iteration']}** - Score: {entry['score']}/10")
                    st.write(f"Assessment: {entry['assessment']}")
                    if entry.get("refined_query"):
                        st.write(f"Refined query: `{entry['refined_query']}`")

                st.write(f"**Total iterations:** {output['iterations']}")
                st.write(f"**Answer confidence:** {output['raw'].get('confidence_in_answer', '?')}")

        with st.expander("Raw JSON"):
            st.json(output.get("raw", {}))

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
        st.write(f"**-->** {g['text']}")
        st.caption(f"Related to {len(g['related_claims'])} claims")
        st.divider()

with tab4:
    st.subheader("Knowledge Graph")
    col1, col2 = st.columns([3, 1])
    with col2:
        min_conf = st.slider("Min contradiction confidence", 0.0, 1.0, 0.7, 0.05)
        rebuild = st.button("Rebuild Graph")

    graph_path = "ui/graph.html"

    if rebuild:
        with st.spinner("Building graph..."):
            from ui.graph_viz import build_graph
            build_graph(output_path=graph_path, min_confidence=min_conf)
        st.success("Graph rebuilt!")

    if os.path.exists(graph_path):
        with open(graph_path, "r", encoding="utf-8") as f:
            html = f.read()
        import streamlit.components.v1 as components
        components.html(html, height=750, scrolling=False)
    else:
        st.info("Click 'Rebuild Graph' to generate the visualization.")
