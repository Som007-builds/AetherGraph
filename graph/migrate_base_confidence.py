# graph/migrate_base_confidence.py
"""
One-time migration: copies current confidence → base_confidence on all
Claim nodes that don't have it set yet.

Safe to run multiple times — only touches claims where base_confidence IS NULL.

Run BEFORE first use of confidence_updater.py:
    python graph/migrate_base_confidence.py
"""
from graph.neo4j_client import run_write, run_query


def run():
    # Count claims that need the migration
    result = run_query("""
        MATCH (c:Claim)
        WHERE c.base_confidence IS NULL
        RETURN count(c) AS n
    """)
    n = result[0]["n"]

    if n == 0:
        print("Migration already applied — all claims have base_confidence.")
        return

    print(f"Setting base_confidence on {n} claims...")

    run_write("""
        MATCH (c:Claim)
        WHERE c.base_confidence IS NULL
        SET c.base_confidence = c.confidence
    """)

    # Verify
    result = run_query("""
        MATCH (c:Claim)
        WHERE c.base_confidence IS NULL
        RETURN count(c) AS remaining
    """)
    remaining = result[0]["remaining"]
    print(f"Migration complete. Claims still missing base_confidence: {remaining}")
    assert remaining == 0, "Migration incomplete — check Neo4j connection"


if __name__ == "__main__":
    run()