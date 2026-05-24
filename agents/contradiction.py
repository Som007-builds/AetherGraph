import json
from config import CONTRADICTION_THRESHOLD
from graph.neo4j_queries import get_all_claims, insert_relationship, get_contradictions
from embeddings.store import find_similar_claims
from llm import call_llm

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
        paper_b=claim_b["paper_title"]
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


def run_contradiction_detection():
    all_claims = get_all_claims()
    print(f"Running contradiction detection on {len(all_claims)} claims...")

    relationships_found = 0
    pairs_checked = set()

    for claim in all_claims:
        similar = find_similar_claims(claim["text"], n_results=8)

        for sim in similar:
            other_claim_id = int(sim["doc_id"].replace("claim_", ""))

            pair_key = tuple(sorted([claim["id"], other_claim_id]))
            if pair_key in pairs_checked:
                continue
            pairs_checked.add(pair_key)

            if sim["distance"] > CONTRADICTION_THRESHOLD:
                continue

            other_claims = [c for c in all_claims if c["id"] == other_claim_id]
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
                confidence=result["confidence"]
            )

            relationships_found += 1

            if result["relationship"] == "CONTRADICTS":
                print(f"\n  CONTRADICTION (confidence: {result['confidence']:.2f})")
                print(f"  A: {claim['text'][:80]}")
                print(f"  B: {other_claim['text'][:80]}")
                print(f"  Reason: {result['explanation']}")

    print(f"\nDone. Found {relationships_found} relationships.")
    return relationships_found


if __name__ == "__main__":
    run_contradiction_detection()