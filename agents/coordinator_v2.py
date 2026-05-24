# agents/coordinator_v2.py
"""
Coordinator v2 — Multi-step agentic loop.

Architecture:
  1. Planner: decides what to search for
  2. Retriever: executes searches against ChromaDB + SQLite
  3. Reflector: evaluates whether context is sufficient
     - If sufficient OR iteration limit hit → Synthesizer
     - If not → refine query, loop back to Retriever
  4. Synthesizer: writes final cited report

Max iterations: 3
"""

from agents.planner import make_plan
from agents.reflector import reflect
from agents.synthesizer import synthesize, format_report
from embeddings.store import find_similar_claims
from graph.queries import get_contradictions, get_gaps

MAX_ITERATIONS = 3


def _retrieve(query: str, fetch_contradictions: bool, fetch_gaps: bool) -> dict:
    raw_claims = find_similar_claims(query, n_results=12)
    claims = []
    claim_ids = set()

    for r in raw_claims:
        claim_id = int(r["doc_id"].replace("claim_", ""))
        claims.append({
            "id": claim_id,
            "text": r["text"],
            "arxiv_id": r["metadata"].get("arxiv_id", "?"),
            "section": r["metadata"].get("section", "?"),
            "distance": r["distance"]
        })
        claim_ids.add(claim_id)

    contradictions = []
    if fetch_contradictions:
        all_contradictions = get_contradictions()
        contradictions = [
            c for c in all_contradictions
            if c.get("claim_a_id") in claim_ids or c.get("claim_b_id") in claim_ids
        ][:6]

    gaps = []
    if fetch_gaps:
        all_gaps = get_gaps()
        gaps = [
            g for g in all_gaps
            if any(cid in claim_ids for cid in g.get("related_claims", []))
        ][:6]

    return {"claims": claims, "contradictions": contradictions, "gaps": gaps}


def _merge_contexts(ctx_a: dict, ctx_b: dict) -> dict:
    seen_claim_ids = {c["id"] for c in ctx_a["claims"]}
    seen_contra_ids = {c.get("id") for c in ctx_a["contradictions"]}
    seen_gap_ids = {g.get("id") for g in ctx_a["gaps"]}

    merged_claims = list(ctx_a["claims"])
    for c in ctx_b["claims"]:
        if c["id"] not in seen_claim_ids:
            merged_claims.append(c)
            seen_claim_ids.add(c["id"])

    merged_contras = list(ctx_a["contradictions"])
    for c in ctx_b["contradictions"]:
        if c.get("id") not in seen_contra_ids:
            merged_contras.append(c)
            seen_contra_ids.add(c.get("id"))

    merged_gaps = list(ctx_a["gaps"])
    for g in ctx_b["gaps"]:
        if g.get("id") not in seen_gap_ids:
            merged_gaps.append(g)
            seen_gap_ids.add(g.get("id"))

    return {
        "claims": merged_claims,
        "contradictions": merged_contras,
        "gaps": merged_gaps
    }


def run(research_question: str, verbose: bool = True) -> dict:
    """
    Main entry point for Coordinator v2.

    Returns dict with keys:
      report, raw, iterations, plan, reflection_log, context
    """
    log = []

    if verbose:
        print(f"\n{'='*60}")
        print(f"Coordinator v2 | Question: {research_question}")
        print(f"{'='*60}")

    # ── Step 1: Plan ──────────────────────────────────────────────
    if verbose:
        print("\n[1/4] Planner — deciding retrieval strategy...")

    plan = make_plan(research_question)

    if verbose:
        print(f"  Sub-queries: {plan['sub_queries']}")
        print(f"  Fetch contradictions: {plan['fetch_contradictions']}")
        print(f"  Fetch gaps: {plan['fetch_gaps']}")
        print(f"  Reasoning: {plan['reasoning']}")

    # ── Steps 2–3: Retrieve → Reflect loop ────────────────────────
    accumulated_context = {"claims": [], "contradictions": [], "gaps": []}
    iteration = 0
    current_queries = plan["sub_queries"]

    while iteration < MAX_ITERATIONS:
        iteration += 1

        if verbose:
            print(f"\n[2/4] Retriever — iteration {iteration}/{MAX_ITERATIONS}")
            for q in current_queries:
                print(f"  Searching: '{q}'")

        iteration_context = {"claims": [], "contradictions": [], "gaps": []}
        for query in current_queries:
            retrieved = _retrieve(
                query=query,
                fetch_contradictions=plan["fetch_contradictions"],
                fetch_gaps=plan["fetch_gaps"]
            )
            iteration_context = _merge_contexts(iteration_context, retrieved)

        accumulated_context = _merge_contexts(accumulated_context, iteration_context)

        if verbose:
            print(f"  Total context: {len(accumulated_context['claims'])} claims, "
                  f"{len(accumulated_context['contradictions'])} contradictions, "
                  f"{len(accumulated_context['gaps'])} gaps")

        # ── Step 3: Reflect ───────────────────────────────────────
        if verbose:
            print(f"\n[3/4] Reflector — evaluating context sufficiency...")

        reflection = reflect(research_question, accumulated_context)
        log.append({
            "iteration": iteration,
            "score": reflection["score"],
            "sufficient": reflection["sufficient"],
            "assessment": reflection["assessment"],
            "refined_query": reflection.get("refined_query")
        })

        if verbose:
            print(f"  Score: {reflection['score']}/10")
            print(f"  Assessment: {reflection['assessment']}")
            print(f"  Sufficient: {reflection['sufficient']}")

        if reflection["sufficient"]:
            if verbose:
                print(f"  → Context approved. Proceeding to synthesis.")
            break

        if iteration >= MAX_ITERATIONS:
            if verbose:
                print(f"  → Iteration limit reached. Synthesizing with available context.")
            break

        refined = reflection.get("refined_query")
        if refined:
            current_queries = [refined]
            if verbose:
                print(f"  → Refining search: '{refined}'")
        else:
            if verbose:
                print(f"  → No refined query provided. Proceeding anyway.")
            break

    # ── Step 4: Synthesize ────────────────────────────────────────
    if verbose:
        print(f"\n[4/4] Synthesizer — writing cited report...")

    result = synthesize(research_question, accumulated_context)
    report = format_report(research_question, result, iterations_taken=iteration)

    if verbose:
        print(f"\n{'='*60}")
        print("Report generated.")
        print(f"{'='*60}")

    return {
        "report": report,
        "raw": result,
        "iterations": iteration,
        "plan": plan,
        "reflection_log": log,
        "context": accumulated_context
    }