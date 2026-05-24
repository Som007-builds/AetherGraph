import json
from graph.neo4j_queries import get_all_claims, insert_gap, get_gaps
from embeddings.store import find_similar_claims
from llm import call_llm

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


def extract_future_work_gaps(section_text: str) -> list[int]:
    """Mine future work / limitations sections for open questions."""
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
            # Store with empty related_claim_ids — paper-level gap
            gap_id = insert_gap(
                gap_text=question,
                related_claim_ids=[]
            )
            gap_ids.append(gap_id)
            print(f"  Gap (future work): {question[:80]}")
    except Exception as e:
        print(f"  Warning: future work gap parsing error — {e}")

    return gap_ids


def find_cluster_gaps(n_clusters: int = 10) -> list[int]:
    """
    For a sample of claims, get their neighbors and ask the LLM
    what research question the cluster circles but never answers.
    """
    all_claims = get_all_claims()
    if len(all_claims) < 5:
        print("  Not enough claims in DB. Run ingestion first.")
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
            cid = int(n["doc_id"].replace("claim_", ""))
            cluster_claim_ids.append(cid)

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
                gap_text=gap_text,
                related_claim_ids=cluster_claim_ids
            )
            gap_ids.append(gap_id)
            print(f"  Gap (cluster): {gap_text[:80]}")

        except Exception as e:
            print(f"  Warning: cluster gap error — {e}")

    return gap_ids


def run_gap_finding():
    """Main entry point for gap finding."""
    total_gaps = 0

    print("Finding cluster gaps...")
    cluster_gap_ids = find_cluster_gaps(n_clusters=10)
    total_gaps += len(cluster_gap_ids)

    print(f"\nTotal gaps found: {total_gaps}")
    return total_gaps


if __name__ == "__main__":
    run_gap_finding()