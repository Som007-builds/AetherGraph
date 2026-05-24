# agents/temporal.py
"""
Temporal reasoning agent.

Capabilities:
  1. get_claims_by_year_range  — semantic search filtered by year
  2. get_consensus_evolution   — how agreement on a topic changed year by year
  3. get_contradiction_timeline — when disputes appeared and whether they resolved

# TODO: replace with Neo4j query in Phase 4
"""

import json
from collections import defaultdict
from llm import call_llm
from graph.queries import get_claims_in_year_range, get_all_claims, get_contradictions
from embeddings.store import find_similar_claims


# ─────────────────────────────────────────────────────────────
# Capability 1: Year-filtered semantic search
# ─────────────────────────────────────────────────────────────

def get_claims_by_year_range(topic: str, year_start: int,
                              year_end: int, n_results: int = 15) -> list[dict]:
    """
    Semantic search for claims about a topic, filtered to a year range.
    Post-filters ChromaDB results by paper_year metadata.
    # TODO: replace with Neo4j query in Phase 4
    """
    raw_results = find_similar_claims(topic, n_results=n_results * 3)

    filtered = []
    for r in raw_results:
        year = r["metadata"].get("paper_year")
        if year is not None:
            try:
                year = int(year)
                if year_start <= year <= year_end:
                    filtered.append({
                        "id": int(r["doc_id"].replace("claim_", "")),
                        "text": r["text"],
                        "arxiv_id": r["metadata"].get("arxiv_id", "?"),
                        "paper_year": year,
                        "distance": r["distance"]
                    })
            except (ValueError, TypeError):
                continue

    filtered.sort(key=lambda x: (x["distance"], x["paper_year"]))
    return filtered[:n_results]


# ─────────────────────────────────────────────────────────────
# Capability 2: Consensus evolution
# ─────────────────────────────────────────────────────────────

EVOLUTION_PROMPT = """You are a science historian analyzing how a research field's consensus changed over time.

Topic: "{topic}"

Here are claims about this topic, grouped by year:

{claims_by_year}

For each year that has claims, describe:
- What position the field was taking that year
- Whether it agreed, disagreed, or was uncertain compared to the previous year
- Any notable shift in language or framing

Then write an overall narrative of how consensus evolved from {year_start} to {year_end}.

Return ONLY valid JSON, no other text:
{{
  "yearly_positions": [
    {{
      "year": 2022,
      "position": "one sentence describing what the field believed this year",
      "shift_from_prior": "same | strengthened | weakened | reversed | first_appearance",
      "key_claim_arxiv_ids": ["arxiv_id_1"]
    }}
  ],
  "overall_narrative": "2-3 sentences describing the arc of consensus change",
  "current_status": "settled | active_debate | fragmented | emerging",
  "confidence": 0.0
}}
"""


def get_consensus_evolution(topic: str, year_start: int = 2020,
                             year_end: int = 2025) -> dict:
    """
    Traces how the field's consensus on a topic evolved year by year.
    # TODO: replace with Neo4j query in Phase 4
    """
    claims = get_claims_by_year_range(topic, year_start, year_end, n_results=40)

    if len(claims) < 3:
        return {
            "yearly_positions": [],
            "overall_narrative": f"Not enough claims in the graph about '{topic}' for temporal analysis. Ingest more papers from {year_start}-{year_end}.",
            "current_status": "insufficient_data",
            "confidence": 0.0
        }

    by_year = defaultdict(list)
    for c in claims:
        by_year[c["paper_year"]].append(c)

    claims_by_year_text = ""
    for year in sorted(by_year.keys()):
        claims_by_year_text += f"\n{year}:\n"
        for c in by_year[year][:4]:
            claims_by_year_text += f"  [{c['arxiv_id']}] {c['text'][:120]}\n"

    prompt = EVOLUTION_PROMPT.format(
        topic=topic,
        claims_by_year=claims_by_year_text,
        year_start=year_start,
        year_end=year_end
    )

    raw = call_llm(prompt, max_tokens=1500)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        result = json.loads(raw[start:]) if start != -1 else {}

    result["claims_by_year"] = {
        str(year): claims_list for year, claims_list in by_year.items()
    }

    return result


# ─────────────────────────────────────────────────────────────
# Capability 3: Contradiction timeline
# ─────────────────────────────────────────────────────────────

CONTRADICTION_TIMELINE_PROMPT = """You are analyzing the history of a scientific dispute.

Topic: "{topic}"

Here are contradictions between papers, with the year of each paper's claims:

{contradiction_text}

For each contradiction:
- When did the dispute first appear?
- Is it still active (both positions still defended in recent papers) or resolved?
- If resolved, which position won and when?

Return ONLY valid JSON, no other text:
{{
  "disputes": [
    {{
      "description": "what the dispute is about",
      "first_appeared": 2022,
      "status": "active | resolved | fading",
      "resolution": "which position appears to have won, or null if unresolved",
      "resolution_year": null
    }}
  ],
  "summary": "one paragraph on the overall dispute landscape for this topic"
}}
"""


def get_contradiction_timeline(topic: str) -> dict:
    """
    Finds contradictions related to a topic and analyzes when they appeared
    and whether they have been resolved.
    # TODO: replace with Neo4j query in Phase 4
    """
    relevant_claims = get_claims_by_year_range(topic, 2019, 2026, n_results=20)
    relevant_ids = {c["id"] for c in relevant_claims}

    all_contradictions = get_contradictions()
    topic_contradictions = [
        c for c in all_contradictions
        if c.get("claim_a_id") in relevant_ids or c.get("claim_b_id") in relevant_ids
    ]

    if not topic_contradictions:
        return {
            "disputes": [],
            "summary": f"No contradictions found related to '{topic}' in the current graph."
        }

    year_by_id = {c["id"]: c["paper_year"] for c in relevant_claims}
    all_claims = get_all_claims()
    for c in all_claims:
        if c["id"] not in year_by_id and c["paper_year"]:
            year_by_id[c["id"]] = c["paper_year"]

    contradiction_text = ""
    for contra in topic_contradictions[:8]:
        year_a = year_by_id.get(contra.get("claim_a_id"), "unknown")
        year_b = year_by_id.get(contra.get("claim_b_id"), "unknown")
        contradiction_text += (
            f"\n- [{year_a}] {contra.get('claim_a', '')[:100]}\n"
            f"  CONTRADICTS\n"
            f"  [{year_b}] {contra.get('claim_b', '')[:100]}\n"
            f"  Reason: {contra.get('explanation', '')[:80]}\n"
        )

    prompt = CONTRADICTION_TIMELINE_PROMPT.format(
        topic=topic,
        contradiction_text=contradiction_text
    )

    raw = call_llm(prompt, max_tokens=1000)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        result = json.loads(raw[start:]) if start != -1 else {}

    return result