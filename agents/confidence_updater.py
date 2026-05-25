# agents/confidence_updater.py
"""
Dynamic confidence recalculation.

Every claim has a base_confidence set at extraction time (by reader.py).
After each contradiction detection run, this module recalculates every
claim's live confidence score based on how many SUPPORTS and CONTRADICTS
edges it has accumulated.

Formula:
    new_confidence = base_confidence
        + 0.08 × support_count
        - 0.12 × contradiction_count
    Clamped to [0.05, 0.98]

Asymmetry is intentional: direct contradiction is rarer and more
deliberate than replication-style support, so it carries more weight.

Phase 7 note: recalculate_all() returns a pure dict — no display logic here.
"""

from graph.neo4j_client import run_query, run_write
from utils.logger import get_logger, log_event

logger = get_logger("confidence_updater")

SUPPORT_BOOST       = 0.08
CONTRADICTION_PENALTY = 0.12
MIN_CONFIDENCE      = 0.05
MAX_CONFIDENCE      = 0.98


def recalculate_all() -> dict:
    """
    Recalculate confidence for every claim in the graph.

    Returns:
        {
          total_updated: int,
          boosted: int,          # confidence went up
          penalized: int,        # confidence went down
          unchanged: int,        # delta < 0.001
          avg_delta: float,
          most_boosted: dict | None,
          most_penalized: dict | None,
        }
    """
    log_event(logger, "confidence_update_start", {})

    # Single query: all claims + their incoming edge counts
    claims = run_query("""
        MATCH (c:Claim)
        OPTIONAL MATCH (c)<-[:SUPPORTS]-(s:Claim)
        OPTIONAL MATCH (c)<-[:CONTRADICTS]-(contra:Claim)
        RETURN
            elementId(c)          AS claim_eid,
            c.base_confidence     AS base_confidence,
            c.confidence          AS current_confidence,
            c.text                AS text,
            count(DISTINCT s)     AS support_count,
            count(DISTINCT contra) AS contradiction_count
    """)

    total_updated = 0
    boosted       = 0
    penalized     = 0
    unchanged     = 0
    deltas        = []
    most_boosted  = None
    most_penalized = None
    max_boost     = 0.0
    max_penalty   = 0.0

    for claim in claims:
        base = claim.get("base_confidence")
        if base is None:
            # Shouldn't happen after migrate_base_confidence.py, but be safe
            continue

        supports       = claim.get("support_count", 0) or 0
        contradictions = claim.get("contradiction_count", 0) or 0

        new_conf = base + (SUPPORT_BOOST * supports) - (CONTRADICTION_PENALTY * contradictions)
        new_conf = round(max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, new_conf)), 4)

        current   = claim.get("current_confidence") or base
        delta     = new_conf - current
        abs_delta = abs(delta)

        if abs_delta < 0.001:
            unchanged += 1
            continue

        run_write("""
            MATCH (c:Claim) WHERE elementId(c) = $eid
            SET c.confidence             = $new_conf,
                c.confidence_updated_at  = datetime(),
                c.support_count          = $supports,
                c.contradiction_count    = $contradictions
        """, {
            "eid":            claim["claim_eid"],
            "new_conf":       new_conf,
            "supports":       supports,
            "contradictions": contradictions,
        })

        total_updated += 1
        deltas.append(abs_delta)

        if delta > 0:
            boosted += 1
            if delta > max_boost:
                max_boost    = delta
                most_boosted = {
                    "text":         claim["text"][:100],
                    "base":         round(base, 3),
                    "new":          new_conf,
                    "delta":        round(delta, 3),
                    "supports":     supports,
                }
        else:
            penalized += 1
            if abs_delta > max_penalty:
                max_penalty    = abs_delta
                most_penalized = {
                    "text":           claim["text"][:100],
                    "base":           round(base, 3),
                    "new":            new_conf,
                    "delta":          round(delta, 3),
                    "contradictions": contradictions,
                }

    avg_delta = round(sum(deltas) / len(deltas), 4) if deltas else 0.0

    summary = {
        "total_updated":  total_updated,
        "boosted":        boosted,
        "penalized":      penalized,
        "unchanged":      unchanged,
        "avg_delta":      avg_delta,
        "most_boosted":   most_boosted,
        "most_penalized": most_penalized,
    }

    log_event(logger, "confidence_update_complete", summary)
    return summary


def get_confidence_distribution() -> dict:
    """
    Returns the current confidence distribution across all claims.
    Used by the UI sidebar health panel.
    """
    result = run_query("""
        MATCH (c:Claim)
        RETURN
            count(c)                                                   AS total,
            avg(c.confidence)                                          AS avg_confidence,
            min(c.confidence)                                          AS min_confidence,
            max(c.confidence)                                          AS max_confidence,
            count(CASE WHEN c.confidence >= 0.8  THEN 1 END)          AS high_confidence,
            count(CASE WHEN c.confidence >= 0.5
                        AND c.confidence < 0.8   THEN 1 END)          AS medium_confidence,
            count(CASE WHEN c.confidence < 0.5   THEN 1 END)          AS low_confidence
    """)
    return result[0] if result else {}


def get_most_changed_claims(limit: int = 10) -> list[dict]:
    """
    Returns the claims whose confidence has moved most from base_confidence.
    Used by the Graph Evolution UI tab.
    """
    return run_query("""
        MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
        WHERE c.base_confidence IS NOT NULL
        WITH c, p, c.confidence - c.base_confidence AS delta
        ORDER BY abs(delta) DESC
        LIMIT $limit
        RETURN
            c.text                                   AS text,
            c.base_confidence                        AS base,
            c.confidence                             AS current,
            c.confidence - c.base_confidence         AS delta,
            coalesce(c.support_count, 0)             AS supports,
            coalesce(c.contradiction_count, 0)       AS contradictions,
            p.arxiv_id                               AS arxiv_id,
            p.title                                  AS paper_title
    """, {"limit": limit})