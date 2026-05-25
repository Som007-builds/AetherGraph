# ui/experiments.py
"""
Experiment card renderer for Streamlit.

Renders a single experiment design dict (from experiment_recommender.py)
as a structured card inside the Contradictions tab.

Phase 7 note: replace st.* calls with your framework's components.
The data contract is the experiment dict returned by design_experiment().
This file contains ONLY display logic — no agent calls happen here
except when the user clicks "Design experiment" to trigger on-demand generation.
"""

import streamlit as st


def render_experiment_card(experiment: dict | None, contradiction: dict) -> None:
    """
    Render an experiment design card for a contradiction.

    If no experiment exists yet, shows a "Design experiment" button.
    If an experiment exists, renders the full card.

    Args:
        experiment:    dict from get_experiment_for_contradiction(), or None
        contradiction: the contradiction dict from get_contradictions()
    """
    if experiment is None:
        _render_design_button(contradiction)
        return

    exp_data     = experiment.get("experiment", {})
    design_conf  = experiment.get("confidence_in_design", 0)

    st.markdown(f"#### 🧪 {exp_data.get('title', 'Experiment Design')}")
    st.caption(f"Design confidence: {design_conf:.0%}")

    # Hypotheses
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**If Paper A is correct:**")
        st.info(experiment.get("hypothesis_a", "—"))
    with col_b:
        st.markdown("**If Paper B is correct:**")
        st.info(experiment.get("hypothesis_b", "—"))

    # Procedure
    st.markdown("**Procedure**")
    st.write(exp_data.get("procedure", "—"))

    # Key details
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        dataset = exp_data.get("dataset", "?")
        st.metric("Dataset", dataset[:25] + ("…" if len(dataset) > 25 else ""))
    with d2:
        metric = exp_data.get("metric", "?")
        st.metric("Metric", metric[:25] + ("…" if len(metric) > 25 else ""))
    with d3:
        st.metric("Duration", exp_data.get("expected_duration", "?"))
    with d4:
        st.metric("Est. Cost", exp_data.get("cost_estimate", "?"))

    # Decision rule
    st.markdown("**Decision rule**")
    st.success(experiment.get("decision_rule", "—"))

    # Caveats
    if experiment.get("caveats"):
        st.caption(f"⚠️ Caveat: {experiment['caveats']}")

    # Models tested
    if exp_data.get("models"):
        st.caption(f"Models: {exp_data['models']}")


def _render_design_button(contradiction: dict) -> None:
    """Render an on-demand 'Design experiment' button for a contradiction."""
    button_key = f"design_{contradiction.get('id', 'unknown')}"
    if st.button("🔬 Design experiment", key=button_key):
        from agents.experiment_recommender import design_experiment, store_experiment
        with st.spinner("Designing experiment…"):
            exp = design_experiment(contradiction)
        if exp:
            store_experiment(contradiction["id"], exp)
            st.rerun()
        else:
            st.error("Could not design experiment — check logs for details.")