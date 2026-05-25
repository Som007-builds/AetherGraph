# agents/contradiction.py
"""
PHASE 6 CHANGE:
  run_contradiction_detection() now calls recalculate_all() after every
  detection run so claim confidence scores are always up to date after
  new CONTRADICTS/SUPPORTS edges are created.
"""
import json
import logging
from config import CONTRADICTION_THRESHOLD
from graph.neo4j_queries import get_all_claims, insert_relationship, get_contradictions
from embeddings.store import find_similar_claims
from llm import call_llm

logger = logging.getLogger(__name__)


CONTRADICTION_PROMPT = """You are a research analyst determining whether two scientific claims contradict each other.

Claim A (from paper: {paper_a}):
"{claim_a}"

Claim B (from paper: {paper_b}):
"{claim_b}"

Think carefully. Two claims CONTRADICT if:
- They make opposite predictions about the same phenomenon
- They report significantly different results on the same setup
- Accepting one as true logically requires rejecting the other

Two claims SUPPORT each other if:
- They agree on the same finding
- One provides evidence for the other

They are UNRELATED if:
- They are about different phenomena
- They don't logically interact

Return ONLY valid JSON, no other text:
{{
  "relationship": "CONTRADICTS or SUPPORTS or UNRELATED",
  "confidence": 0.0,
  "explanation": "one sentence explaining your judgment"
}}
"""


def check_pair(claim_a: dict, claim_b: dict) -> dict | None:
    if claim_a["id"] == claim_b["id"]:
        return None
    if claim_a["arxiv_id"] == claim_b["arxiv_id"]:
        return None

    prompt = CONTRADICTION_PROMPT.format(
        claim_a=claim_a["text"],
        paper_a=claim_a["paper_title"],
        claim_b=claim_b["text"],
        paper_b=claim_b["paper_title"],
    )

    raw = call_llm(prompt, max_tokens=500)

    # Strip markdown fences if present
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
        if data["relationship"] == "UNRELATED":
            return None
        return data
    except json.JSONDecodeError:
        start = raw.find("{")
        if start != -1:
            try:
                data = json.loads(raw[start:])
                if data["relationship"] == "UNRELATED":
                    return None
                return data
            except json.JSONDecodeError:
                pass
        return None


def run_contradiction_detection(limit_to_claim_ids: list[str] = None) -> int:
    all_claims = get_all_claims()
    
    if limit_to_claim_ids is not None:
        limit_set = set(str(cid) for cid in limit_to_claim_ids)
        target_claims = [c for c in all_claims if str(c["id"]) in limit_set]
        logger.info(f"Running contradiction detection on {len(target_claims)} target claims (out of {len(all_claims)} total)...")
    else:
        target_claims = all_claims
        logger.info(f"Running contradiction detection on all {len(all_claims)} claims...")

    relationships_found = 0
    pairs_checked = set()

    for claim in target_claims:
        similar = find_similar_claims(claim["text"], n_results=8)

        for sim in similar:
            # Neo4j 5+ returns string elementIds — do NOT cast to int
            other_claim_id = sim["doc_id"].replace("claim_", "")

            # Both ids are strings — sorted() is safe
            pair_key = tuple(sorted([str(claim["id"]), other_claim_id]))
            if pair_key in pairs_checked:
                continue
            pairs_checked.add(pair_key)

            if sim["distance"] > CONTRADICTION_THRESHOLD:
                continue

            other_claims = [c for c in all_claims if str(c["id"]) == other_claim_id]
            if not other_claims:
                continue
            other_claim = other_claims[0]

            result = check_pair(claim, other_claim)
            if result is None:
                continue

            insert_relationship(
                claim_a_id=claim["id"],
                claim_b_id=other_claim_id,
                rel_type=result["relationship"],
                explanation=result["explanation"],
                confidence=result["confidence"],
            )

            relationships_found += 1

            if result["relationship"] == "CONTRADICTS":
                logger.info(
                    f"\n  CONTRADICTION (confidence: {result['confidence']:.2f})\n"
                    f"  A: {claim['text'][:80]}\n"
                    f"  B: {other_claim['text'][:80]}\n"
                    f"  Reason: {result['explanation']}"
                )

    logger.info(f"\nDone. Found {relationships_found} relationships.")

    # Phase 6: recalculate confidence scores now that new edges exist
    logger.info("\nRecalculating claim confidence scores...")
    try:
        from agents.confidence_updater import recalculate_all
        summary = recalculate_all()
        logger.info(
            f"  Updated {summary['total_updated']} claims: "
            f"{summary['boosted']} boosted, "
            f"{summary['penalized']} penalized, "
            f"{summary['unchanged']} unchanged"
        )
        if summary.get("most_penalized"):
            mp = summary["most_penalized"]
            logger.info(f"  Most penalized: {mp['text'][:60]}... "
                        f"({mp['base']:.2f} → {mp['new']:.2f})")
    except Exception as e:
        logger.warning(f"  Warning: confidence recalculation failed — {e}")

    return relationships_found


if __name__ == "__main__":
    run_contradiction_detection()