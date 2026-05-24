# graph/fix_empty_gap_links.py
"""
One-time script: finds gaps with no RELATED_TO edges and links them
to their 5 most semantically similar claims.
Safe to run multiple times (uses MERGE).

Usage:
    python graph/fix_empty_gap_links.py
"""
from graph.neo4j_client import run_query, run_write
from embeddings.store import find_similar_claims


def run():
    # Find all gaps with no outgoing RELATED_TO edges
    unlinked = run_query("""
        MATCH (g:Gap)
        WHERE NOT (g)-[:RELATED_TO]->()
        RETURN elementId(g) AS gap_id, g.text AS text
    """)

    print(f"Found {len(unlinked)} unlinked gaps. Linking...")

    fixed = 0
    for gap in unlinked:
        gap_id = gap["gap_id"]
        text = gap["text"]

        similar = find_similar_claims(text, n_results=5)
        linked = 0

        for s in similar:
            raw_id = s["doc_id"].replace("claim_", "")
            if not raw_id:
                continue

            # Look up by elementId string (Neo4j elementId is a string in Neo4j 5+)
            result = run_query("""
                MATCH (c:Claim)
                WHERE elementId(c) = $cid
                RETURN elementId(c) AS neo_id
            """, {"cid": raw_id})

            if not result:
                # Fallback: try matching by claim_id property (set during insert)
                result = run_query("""
                    MATCH (c:Claim {claim_id: $cid})
                    RETURN elementId(c) AS neo_id
                """, {"cid": raw_id})

            if not result:
                continue

            neo_claim_id = result[0]["neo_id"]

            run_write("""
                MATCH (g:Gap) WHERE elementId(g) = $gap_id
                MATCH (c:Claim) WHERE elementId(c) = $claim_id
                MERGE (g)-[:RELATED_TO]->(c)
            """, {"gap_id": gap_id, "claim_id": neo_claim_id})
            linked += 1

        if linked > 0:
            fixed += 1
            print(f"  Linked gap to {linked} claims: {text[:60]}")
        else:
            print(f"  Warning: no claims found for gap: {text[:60]}")

    print(f"\nDone. Fixed {fixed}/{len(unlinked)} gaps.")


if __name__ == "__main__":
    run()