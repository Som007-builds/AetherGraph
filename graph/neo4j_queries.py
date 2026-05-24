# graph/neo4j_queries.py
"""
Neo4j Cypher query layer.
Drop-in replacement for graph/queries.py.
All functions have identical signatures and return formats.
"""
from graph.neo4j_client import run_query, run_write


# ─────────────────────────────────────────────────────────────
# Papers
# ─────────────────────────────────────────────────────────────

def insert_paper(arxiv_id: str, title: str, authors: str,
                 abstract: str, published: str) -> str:
    """
    Insert or update a paper. Returns arxiv_id (used as primary key in Neo4j).
    """
    year = None
    if published and len(published) >= 4:
        try:
            year = int(published[:4])
        except ValueError:
            pass

    run_write("""
        MERGE (p:Paper {arxiv_id: $arxiv_id})
        SET p.title = $title,
            p.authors = $authors,
            p.abstract = $abstract,
            p.published = $published,
            p.year = $year
    """, {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "year": year
    })
    return arxiv_id


def get_paper_by_arxiv_id(arxiv_id: str) -> dict | None:
    results = run_query("""
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        RETURN p.arxiv_id AS arxiv_id, p.title AS title,
               p.authors AS authors, p.abstract AS abstract,
               p.published AS published, p.year AS year
    """, {"arxiv_id": arxiv_id})
    return results[0] if results else None


# ─────────────────────────────────────────────────────────────
# Claims
# ─────────────────────────────────────────────────────────────

def insert_claim(paper_id: str, claim_text: str, section: str,
                 confidence: float = 1.0, embedding_id: str = None,
                 paper_year: int = None) -> int:
    """
    Insert a claim and link it to its paper.
    paper_id is arxiv_id in Neo4j (not SQLite int).
    Returns a synthetic int ID based on Neo4j internal id for ChromaDB compat.
    """
    result = run_write("""
        MATCH (p:Paper {arxiv_id: $arxiv_id})
        CREATE (c:Claim {
            text: $text,
            section: $section,
            confidence: $confidence,
            embedding_id: $embedding_id,
            paper_year: $paper_year
        })
        CREATE (c)-[:EXTRACTED_FROM]->(p)
        SET c.claim_id = elementId(c)
        RETURN elementId(c) AS claim_id
    """, {
        "arxiv_id": paper_id,
        "text": claim_text,
        "section": section,
        "confidence": confidence,
        "embedding_id": embedding_id or "",
        "paper_year": paper_year
    })
    return result[0]["claim_id"] if result else None


def get_all_claims() -> list[dict]:
    results = run_query("""
        MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
        RETURN elementId(c) AS id, c.text AS text, c.section AS section,
               c.confidence AS confidence, p.arxiv_id AS arxiv_id,
               p.title AS paper_title, c.paper_year AS paper_year
    """)
    return results


def get_claims_in_year_range(year_start: int, year_end: int) -> list[dict]:
    """
    Return all claims from papers published within [year_start, year_end].
    Native Cypher range filter — no post-processing needed.
    """
    results = run_query("""
        MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
        WHERE c.paper_year >= $year_start AND c.paper_year <= $year_end
        RETURN elementId(c) AS id, c.text AS text, c.section AS section,
               c.confidence AS confidence, p.arxiv_id AS arxiv_id,
               p.title AS paper_title, c.paper_year AS paper_year
        ORDER BY c.paper_year ASC
    """, {"year_start": year_start, "year_end": year_end})
    return results


# ─────────────────────────────────────────────────────────────
# Relationships
# ─────────────────────────────────────────────────────────────

def insert_relationship(claim_a_id: int, claim_b_id: int,
                        rel_type: str, explanation: str,
                        confidence: float) -> None:
    """
    Insert a CONTRADICTS or SUPPORTS relationship between two claims.
    """
    if rel_type == "CONTRADICTS":
        run_write("""
            MATCH (a:Claim) WHERE elementId(a) = $claim_a_id
            MATCH (b:Claim) WHERE elementId(b) = $claim_b_id
            MERGE (a)-[r:CONTRADICTS]->(b)
            SET r.explanation = $explanation,
                r.confidence = $confidence
        """, {
            "claim_a_id": claim_a_id,
            "claim_b_id": claim_b_id,
            "explanation": explanation,
            "confidence": confidence
        })
    elif rel_type == "SUPPORTS":
        run_write("""
            MATCH (a:Claim) WHERE elementId(a) = $claim_a_id
            MATCH (b:Claim) WHERE elementId(b) = $claim_b_id
            MERGE (a)-[r:SUPPORTS]->(b)
            SET r.explanation = $explanation,
                r.confidence = $confidence
        """, {
            "claim_a_id": claim_a_id,
            "claim_b_id": claim_b_id,
            "explanation": explanation,
            "confidence": confidence
        })


def get_contradictions() -> list[dict]:
    """
    Returns all CONTRADICTS relationships with both claim texts and paper titles.
    Includes claim_a_id and claim_b_id for coordinator v2 matching.
    """
    results = run_query("""
        MATCH (a:Claim)-[r:CONTRADICTS]->(b:Claim)
        MATCH (a)-[:EXTRACTED_FROM]->(pa:Paper)
        MATCH (b)-[:EXTRACTED_FROM]->(pb:Paper)
        RETURN elementId(r) AS id,
               r.explanation AS explanation,
               r.confidence AS confidence,
               a.text AS claim_a,
               pa.title AS paper_a,
               b.text AS claim_b,
               pb.title AS paper_b,
               elementId(a) AS claim_a_id,
               elementId(b) AS claim_b_id
        ORDER BY r.confidence DESC
    """)
    return results


def get_supports() -> list[dict]:
    results = run_query("""
        MATCH (a:Claim)-[r:SUPPORTS]->(b:Claim)
        MATCH (a)-[:EXTRACTED_FROM]->(pa:Paper)
        MATCH (b)-[:EXTRACTED_FROM]->(pb:Paper)
        RETURN elementId(r) AS id,
               r.explanation AS explanation,
               r.confidence AS confidence,
               a.text AS claim_a,
               pa.title AS paper_a,
               b.text AS claim_b,
               pb.title AS paper_b
        ORDER BY r.confidence DESC
    """)
    return results


# ─────────────────────────────────────────────────────────────
# Gaps
# ─────────────────────────────────────────────────────────────

def insert_gap(text: str, source: str, related_claim_ids: list[int]) -> int:
    """
    Insert a research gap and link it to related claims.
    Returns Neo4j internal id.
    """
    result = run_write("""
        CREATE (g:Gap {text: $text, source: $source})
        SET g.gap_id = elementId(g)
        RETURN elementId(g) AS gap_id
    """, {"text": text, "source": source})

    gap_id = result[0]["gap_id"] if result else None

    if gap_id and related_claim_ids:
        for cid in related_claim_ids:
            run_write("""
                MATCH (g:Gap) WHERE elementId(g) = $gap_id
                MATCH (c:Claim) WHERE elementId(c) = $claim_id
                MERGE (g)-[:RELATED_TO]->(c)
            """, {"gap_id": gap_id, "claim_id": cid})

    return gap_id


def get_gaps() -> list[dict]:
    """
    Returns all gaps with their related claim IDs.
    """
    results = run_query("""
        MATCH (g:Gap)
        OPTIONAL MATCH (g)-[:RELATED_TO]->(c:Claim)
        RETURN elementId(g) AS id, g.text AS text, g.source AS source,
               collect(elementId(c)) AS related_claims
    """)
    return results


# ─────────────────────────────────────────────────────────────
# Graph stats
# ─────────────────────────────────────────────────────────────

def get_graph_stats() -> dict:
    result = run_query("""
        MATCH (p:Paper) WITH count(p) AS papers
        MATCH (c:Claim) WITH papers, count(c) AS claims
        MATCH ()-[r:CONTRADICTS]->() WITH papers, claims, count(r) AS contradictions
        MATCH (g:Gap) WITH papers, claims, contradictions, count(g) AS gaps
        RETURN papers, claims, contradictions, gaps
    """)
    return result[0] if result else {}