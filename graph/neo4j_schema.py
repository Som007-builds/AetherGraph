# graph/neo4j_schema.py
"""
Neo4j schema setup.
Creates constraints and indexes.
Run once: python -m graph.neo4j_schema

PHASE 6 ADDITION:
  Added claim_confidence index to support fast confidence-range queries
  used by confidence_updater.py and the Graph Evolution UI tab.
"""
from graph.neo4j_client import run_write


CONSTRAINTS = [
    "CREATE CONSTRAINT paper_arxiv_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.arxiv_id IS UNIQUE",
    "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.claim_id IS UNIQUE",
    "CREATE CONSTRAINT gap_id IF NOT EXISTS FOR (g:Gap) REQUIRE g.gap_id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX claim_year IF NOT EXISTS FOR (c:Claim) ON (c.paper_year)",
    "CREATE INDEX claim_section IF NOT EXISTS FOR (c:Claim) ON (c.section)",
    "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)",
    # Phase 6: confidence queries (distribution, top-N by change)
    "CREATE INDEX claim_confidence IF NOT EXISTS FOR (c:Claim) ON (c.confidence)",
]


def init_neo4j():
    print("Setting up Neo4j constraints and indexes...")
    for stmt in CONSTRAINTS:
        try:
            run_write(stmt)
            print(f"  OK: {stmt[:60]}...")
        except Exception as e:
            print(f"  Skip (already exists): {e}")

    for stmt in INDEXES:
        try:
            run_write(stmt)
            print(f"  OK: {stmt[:60]}...")
        except Exception as e:
            print(f"  Skip (already exists): {e}")

    print("Schema setup complete.")


if __name__ == "__main__":
    init_neo4j()