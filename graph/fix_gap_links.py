# graph/fix_gap_links.py
import sqlite3
import json
from config import DB_PATH
from graph.neo4j_client import run_write, run_query


def run():
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("SELECT id, related_claim_ids FROM gaps").fetchall()
    conn.close()

    linked = 0
    skipped = 0

    for gap_id, related_claim_ids_str in rows:
        if not related_claim_ids_str:
            continue
        try:
            claim_ids = json.loads(related_claim_ids_str)
        except Exception:
            continue

        for cid in claim_ids:
            result = run_write("""
                MATCH (g:Gap {gap_id: $gap_id})
                MATCH (c:Claim {claim_id: $claim_id})
                MERGE (g)-[:RELATED_TO]->(c)
                RETURN count(c) AS matched
            """, {"gap_id": gap_id, "claim_id": cid})

            if result and result[0].get("matched", 0) > 0:
                linked += 1
            else:
                skipped += 1

    print(f"Linked: {linked}  Skipped (claim not found): {skipped}")

    # Verify
    result = run_query("MATCH (g:Gap)-[:RELATED_TO]->(c:Claim) RETURN count(*) AS n")
    print(f"Total RELATED_TO edges in Neo4j: {result[0]['n']}")


if __name__ == "__main__":
    run()