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
    # Phase 8: domain entity nodes
    "CREATE CONSTRAINT benchmark_name IF NOT EXISTS FOR (b:Benchmark) REQUIRE b.name IS UNIQUE",
    "CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX claim_year IF NOT EXISTS FOR (c:Claim) ON (c.paper_year)",
    "CREATE INDEX claim_section IF NOT EXISTS FOR (c:Claim) ON (c.section)",
    "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)",
    # Phase 6: confidence queries (distribution, top-N by change)
    "CREATE INDEX claim_confidence IF NOT EXISTS FOR (c:Claim) ON (c.confidence)",
    # Phase 4: structured claim field indexes
    "CREATE INDEX claim_subject IF NOT EXISTS FOR (c:Claim) ON (c.subject)",
    "CREATE INDEX claim_metric IF NOT EXISTS FOR (c:Claim) ON (c.metric)",
    "CREATE INDEX claim_direction IF NOT EXISTS FOR (c:Claim) ON (c.direction)",
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