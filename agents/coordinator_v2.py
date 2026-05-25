# agents/coordinator_v2.py
"""
Coordinator v2 — Multi-step agentic loop.

Architecture:
  1. Planner: decides what to search for
  2. Retriever: executes searches against ChromaDB + Neo4j
  3. Reflector: evaluates whether context is sufficient
     - If sufficient OR iteration limit hit → Synthesizer
     - If not → refine query, loop back to Retriever
  4. Synthesizer: writes final cited report

Max iterations: 3
"""

from agents.planner import make_plan
from agents.reflector import reflect
from agents.synthesizer import synthesize, format_report
from agents.temporal import get_consensus_evolution
from agents.citation import get_weighted_confidence
from embeddings.store import find_similar_claims
from graph.neo4j_queries import get_contradictions, get_gaps
import logging

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

TEMPORAL_KEYWORDS = [
    "changed", "evolved", "shifting", "still", "anymore", "recent",
    "latest", "trend", "history", "over time", "previously", "used to",
    "now", "currently", "has", "have", "2023", "2024", "2025"
]


def _is_temporal_question(question: str) -> bool:
    return any(kw in question.lower() for kw in TEMPORAL_KEYWORDS)


def _get_temporal_context(question: str) -> str:
    if not _is_temporal_question(question):
        return ""

    topic = " ".join(question.split()[:6])
    try:
        evolution = get_consensus_evolution(topic, year_start=2021, year_end=2025)
        narrative = evolution.get("overall_narrative", "")
        status = evolution.get("current_status", "")
        if narrative:
            return (
                f"\nTEMPORAL CONTEXT (consensus evolution):\n"
                f"Status: {status}\n{narrative}\n"
            )
    except Exception as e:
        logger.warning(f"  [Coordinator v2] Temporal context failed: {e}")

    return ""


def _retrieve(query: str, fetch_contradictions: bool, fetch_gaps: bool) -> dict:
    raw_claims = find_similar_claims(query, n_results=12)
    claims = []
    claim_ids = set()

    for r in raw_claims:
        # elementId is a string in Neo4j 5+ — do NOT cast to int
        claim_id = r["doc_id"].replace("claim_", "")

        base_confidence = 1.0 - float(r.get("distance", 0))
        weighted = get_weighted_confidence(
            claim_id=claim_id,
            base_confidence=base_confidence
        )

        claims.append({
            "id": claim_id,
            "text": r["text"],
            "arxiv_id": r["metadata"].get("arxiv_id", "?"),
            "section": r["metadata"].get("section", "?"),
            "distance": r["distance"],
            "weighted_confidence": weighted
        })
        claim_ids.add(claim_id)

    # Sort by citation-weighted confidence — strongest evidence first
    claims.sort(key=lambda c: c["weighted_confidence"], reverse=True)

    contradictions = []
    if fetch_contradictions:
        all_contradictions = get_contradictions()
        contradictions = [
            c for c in all_contradictions
            if c.get("claim_a_id") in claim_ids
            or c.get("claim_b_id") in claim_ids
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
    seen_claim_ids  = {c["id"] for c in ctx_a["claims"]}
    seen_contra_ids = {c.get("id") for c in ctx_a["contradictions"]}
    seen_gap_ids    = {g.get("id") for g in ctx_a["gaps"]}

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

    # Re-sort merged claims so highest weighted_confidence stays on top
    merged_claims.sort(key=lambda c: c.get("weighted_confidence", 0), reverse=True)

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
        logger.info(f"\n{'='*60}\nCoordinator v2 | Question: {research_question}\n{'='*60}")

    # ── Step 1: Plan ──────────────────────────────────────────────
    if verbose:
        logger.info("\n[1/4] Planner — deciding retrieval strategy...")

    plan = make_plan(research_question)

    if verbose:
        logger.info(f"  Sub-queries: {plan['sub_queries']}")
        logger.info(f"  Fetch contradictions: {plan['fetch_contradictions']}")
        logger.info(f"  Fetch gaps: {plan['fetch_gaps']}")
        logger.info(f"  Reasoning: {plan['reasoning']}")

    # ── Steps 2–3: Retrieve → Reflect loop ────────────────────────
    accumulated_context = {"claims": [], "contradictions": [], "gaps": []}
    iteration = 0
    current_queries = plan["sub_queries"]

    while iteration < MAX_ITERATIONS:
        iteration += 1

        if verbose:
            logger.info(f"\n[2/4] Retriever — iteration {iteration}/{MAX_ITERATIONS}")
            for q in current_queries:
                logger.info(f"  Searching: '{q}'")

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
            logger.info(f"  Total context: {len(accumulated_context['claims'])} claims, "
                        f"{len(accumulated_context['contradictions'])} contradictions, "
                        f"{len(accumulated_context['gaps'])} gaps")
            if accumulated_context["claims"]:
                top = accumulated_context["claims"][0]
                logger.info(f"  Top claim (w={top['weighted_confidence']:.3f}): "
                            f"{top['text'][:70]}...")

        # ── Step 3: Reflect ───────────────────────────────────────
        if verbose:
            logger.info(f"\n[3/4] Reflector — evaluating context sufficiency...")

        reflection = reflect(research_question, accumulated_context)
        log.append({
            "iteration": iteration,
            "score": reflection["score"],
            "sufficient": reflection["sufficient"],
            "assessment": reflection["assessment"],
            "refined_query": reflection.get("refined_query")
        })

        if verbose:
            logger.info(f"  Score: {reflection['score']}/10")
            logger.info(f"  Assessment: {reflection['assessment']}")
            logger.info(f"  Sufficient: {reflection['sufficient']}")

        if reflection["sufficient"]:
            if verbose:
                logger.info(f"  → Context approved. Proceeding to synthesis.")
            break

        if iteration >= MAX_ITERATIONS:
            if verbose:
                logger.info(f"  → Iteration limit reached. Synthesizing with available context.")
            break

        refined = reflection.get("refined_query")
        if refined:
            current_queries = [refined]
            if verbose:
                logger.info(f"  → Refining search: '{refined}'")
        else:
            if verbose:
                logger.info(f"  → No refined query. Proceeding to synthesis.")
            break

    # ── Optional: temporal context injection ──────────────────────
    temporal_context_str = _get_temporal_context(research_question)
    if temporal_context_str and verbose:
        logger.info(f"\n[+] Temporal context injected")
    accumulated_context["temporal_note"] = temporal_context_str

    # ── Step 4: Synthesize ────────────────────────────────────────
    if verbose:
        logger.info(f"\n[4/4] Synthesizer — writing cited report...")

    result = synthesize(research_question, accumulated_context)
    report = format_report(research_question, result, iterations_taken=iteration)

    if verbose:
        logger.info(f"\n{'='*60}\nReport generated.\n{'='*60}")

    return {
        "report": report,
        "raw": result,
        "iterations": iteration,
        "plan": plan,
        "reflection_log": log,
        "context": accumulated_context
    }