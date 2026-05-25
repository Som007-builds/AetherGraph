import json
import logging
from graph.neo4j_queries import get_all_claims, insert_gap, get_gaps
from embeddings.store import find_similar_claims
from llm import call_llm

logger = logging.getLogger(__name__)


FUTURE_WORK_PROMPT = """You are analyzing the "Future Work" or "Limitations" section of an AI research paper.

Extract the open research questions this paper explicitly says it did NOT answer.
Return each as a standalone research question a future paper could address.

Section text:
---
{text}
---

Return ONLY valid JSON, no other text:
{{
  "open_questions": [
    "A specific research question this paper left unanswered"
  ]
}}
"""

CLUSTER_GAP_PROMPT = """You are analyzing a cluster of related research claims from multiple papers.

These claims all relate to the same topic, but together they reveal what's missing.

Claims:
{claims}

Think carefully: What important question do these claims collectively circle around but none of them directly answer?
The gap should be:
- Specific enough to be a research question
- Not already answered by any of the claims above
- Something the field would care about

Return ONLY valid JSON, no other text:
{{
  "gap": "The specific unanswered research question",
  "reasoning": "Why none of the above claims actually answers this",
  "confidence": 0.0
}}
"""


def _resolve_similar_claim_ids(query_text: str, n: int = 5) -> list:
    """
    Find n semantically similar claims for a query text.
    Returns a list of Neo4j element IDs (strings).
    """
    similar = find_similar_claims(query_text, n_results=n)
    ids = []
    for s in similar:
        doc_id = s.get("doc_id", "")
        # doc_id format is "claim_<elementId>" — strip prefix
        raw_id = doc_id.replace("claim_", "")
        if raw_id:
            ids.append(raw_id)
    return ids


def extract_future_work_gaps(section_text: str) -> list:
    """
    Mine future work / limitations sections for open questions.
    Each gap is now auto-linked to the 5 most semantically similar claims
    in ChromaDB so it surfaces in coordinator filtering.
    Returns list of gap_ids inserted.
    """
    if len(section_text.strip()) < 50:
        return []

    prompt = FUTURE_WORK_PROMPT.format(text=section_text[:2000])
    raw = call_llm(prompt, max_tokens=800)

    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    gap_ids = []
    try:
        data = json.loads(raw)
        for question in data.get("open_questions", []):
            if len(question) < 20:
                continue

            # Auto-link to semantically similar claims — fixes empty related_claims
            related_claim_ids = _resolve_similar_claim_ids(question, n=5)

            gap_id = insert_gap(
                text=question,
                source="future_work",
                related_claim_ids=related_claim_ids
            )
            gap_ids.append(gap_id)
            logger.info(f"  Gap (future_work, {len(related_claim_ids)} links): {question[:70]}")

    except Exception as e:
        logger.warning(f"  Warning: future work gap parsing error — {e}")

    return gap_ids


def find_cluster_gaps(n_clusters: int = 10) -> list:
    """
    For a sample of claims, get their neighbors and ask the LLM
    what research question the cluster circles but never answers.
    """
    all_claims = get_all_claims()
    if len(all_claims) < 5:
        logger.warning("  Not enough claims in DB. Run ingestion first.")
        return []

    step = max(1, len(all_claims) // n_clusters)
    seed_claims = all_claims[::step][:n_clusters]

    gap_ids = []

    for seed in seed_claims:
        neighbors = find_similar_claims(seed["text"], n_results=6)

        if len(neighbors) < 3:
            continue

        claims_text = ""
        cluster_claim_ids = []
        for i, n in enumerate(neighbors):
            claims_text += f"{i+1}. [{n['metadata'].get('arxiv_id', '?')}] {n['text']}\n"
            raw_id = n["doc_id"].replace("claim_", "")
            if raw_id:
                cluster_claim_ids.append(raw_id)

        prompt = CLUSTER_GAP_PROMPT.format(claims=claims_text)
        raw = call_llm(prompt, max_tokens=500)

        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            data = json.loads(raw)
            gap_text = data.get("gap", "")
            confidence = data.get("confidence", 0)

            if len(gap_text) < 20 or confidence < 0.5:
                continue

            gap_id = insert_gap(
                text=gap_text,
                source="cluster",
                related_claim_ids=cluster_claim_ids
            )
            gap_ids.append(gap_id)
            logger.info(f"  Gap (cluster, {len(cluster_claim_ids)} links): {gap_text[:70]}")

        except Exception as e:
            logger.warning(f"  Warning: cluster gap error — {e}")

    return gap_ids


def run_gap_finding():
    """Main entry point for gap finding."""
    total_gaps = 0

    logger.info("Finding cluster gaps...")
    cluster_gap_ids = find_cluster_gaps(n_clusters=10)
    total_gaps += len(cluster_gap_ids)

    logger.info(f"\nTotal gaps found: {total_gaps}")
    return total_gaps


if __name__ == "__main__":
    run_gap_finding()