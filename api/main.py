# api/main.py
"""
SciMesh FastAPI backend.
Wraps all existing Python functions as HTTP endpoints.
Run with: uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json

from api.models import (
    GraphStats, ClaimsResponse, ContradictionsResponse, ContradictionModel,
    ExperimentModel, GapsResponse, CoordinatorOutput, IngestionSummary,
    ConfidenceDistribution, ChangedClaim, TemporalEvolution, DisputeTimeline
)

app = FastAPI(
    title="SciMesh API",
    description="Multi-agent AI research knowledge graph",
    version="1.70"
)

# Allow Next.js (3000) or React (5173) dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_experiment_for_frontend(exp_dict: dict) -> dict:
    e = exp_dict.get("experiment", {})
    caveats_val = exp_dict.get("caveats", "")
    if isinstance(caveats_val, str):
        caveats_list = [caveats_val] if caveats_val else []
    elif isinstance(caveats_val, list):
        caveats_list = caveats_val
    else:
        caveats_list = []
        
    return {
        "contradiction_id": exp_dict.get("contradiction_id", ""),
        "title": e.get("title", "Experiment Design"),
        "hypothesis_a": exp_dict.get("hypothesis_a", ""),
        "hypothesis_b": exp_dict.get("hypothesis_b", ""),
        "procedure": e.get("procedure", ""),
        "dataset": e.get("dataset", ""),
        "duration": e.get("expected_duration", ""),
        "cost": e.get("cost_estimate", ""),
        "decision_rule": exp_dict.get("decision_rule", ""),
        "caveats": caveats_list,
        "design_confidence": exp_dict.get("confidence_in_design", 0.0)
    }


# ─── Graph Stats ──────────────────────────────────────────────────────────────

@app.get("/api/stats", response_model=GraphStats)
def get_stats():
    from graph.neo4j_queries import get_graph_stats
    from graph.neo4j_client import run_query
    stats = get_graph_stats()
    
    # Query count of experiments
    exp_res = run_query("MATCH ()-[r:CONTRADICTS]->() WHERE r.experiment_design IS NOT NULL RETURN count(r) AS n")
    exp_count = exp_res[0]["n"] if exp_res else 0
    
    return {
        "papers": stats.get("papers", 0),
        "claims": stats.get("claims", 0),
        "contradictions": stats.get("contradictions", 0),
        "gaps": stats.get("gaps", 0),
        "experiments": exp_count
    }


# ─── Claims ───────────────────────────────────────────────────────────────────

@app.get("/api/claims", response_model=ClaimsResponse)
def get_claims(limit: int = 50, offset: int = 0):
    from graph.neo4j_queries import get_all_claims
    claims = get_all_claims()
    formatted_claims = []
    for c in claims:
        formatted_claims.append({
            "id": str(c.get("id")),
            "text": c.get("text", ""),
            "section": c.get("section", ""),
            "confidence": c.get("confidence", 0.0),
            "base_confidence": c.get("base_confidence"),
            "arxiv_id": c.get("arxiv_id", ""),
            "paper_year": c.get("paper_year"),
            "paper_title": c.get("paper_title")
        })
    return {
        "total": len(formatted_claims),
        "claims": formatted_claims[offset:offset + limit]
    }


# ─── Contradictions ───────────────────────────────────────────────────────────

@app.get("/api/contradictions", response_model=ContradictionsResponse)
def get_contradictions(min_confidence: float = 0.0, limit: int = 50):
    from graph.neo4j_queries import get_contradictions
    from agents.experiment_recommender import get_experiment_for_contradiction
    all_c = get_contradictions()
    filtered = [c for c in all_c if c.get("confidence", 0) >= min_confidence]
    
    formatted = []
    for c in filtered[:limit]:
        exp = get_experiment_for_contradiction(c["id"])
        
        formatted.append({
            "id": str(c["id"]),
            "claim_a": {
                "id": str(c.get("claim_a_id", "")),
                "text": c.get("claim_a", ""),
                "section": "Unknown",
                "confidence": c.get("confidence", 0.0),
                "arxiv_id": ""
            },
            "claim_b": {
                "id": str(c.get("claim_b_id", "")),
                "text": c.get("claim_b", ""),
                "section": "Unknown",
                "confidence": c.get("confidence", 0.0),
                "arxiv_id": ""
            },
            "paper_a": c.get("paper_a", ""),
            "paper_b": c.get("paper_b", ""),
            "explanation": c.get("explanation", ""),
            "confidence": c.get("confidence", 0.0),
            "has_experiment": exp is not None
        })
        
    return {
        "total": len(filtered),
        "contradictions": formatted
    }


# ─── Experiments ──────────────────────────────────────────────────────────────

@app.get("/api/experiments/{contradiction_id}", response_model=ExperimentModel)
def get_experiment(contradiction_id: str):
    from agents.experiment_recommender import get_experiment_for_contradiction
    exp = get_experiment_for_contradiction(contradiction_id)
    if not exp:
        raise HTTPException(status_code=404, detail="No experiment designed yet")
    return format_experiment_for_frontend(exp)


@app.post("/api/experiments/{contradiction_id}/design", response_model=ExperimentModel)
def design_experiment(contradiction_id: str):
    """Design an experiment for a specific contradiction on demand."""
    from graph.neo4j_queries import get_contradictions
    from agents.experiment_recommender import design_experiment, store_experiment

    all_c = get_contradictions()
    contradiction = next((c for c in all_c if str(c["id"]) == contradiction_id), None)
    if not contradiction:
        raise HTTPException(status_code=404, detail="Contradiction not found")

    exp = design_experiment(contradiction)
    if not exp:
        raise HTTPException(status_code=500, detail="Experiment design failed")

    store_experiment(contradiction_id, exp)
    return format_experiment_for_frontend(exp)


# ─── Research Gaps ────────────────────────────────────────────────────────────

@app.get("/api/gaps", response_model=GapsResponse)
def get_gaps(source: Optional[str] = None):
    from graph.neo4j_queries import get_gaps
    gaps = get_gaps()
    if source:
        gaps = [g for g in gaps if g.get("source") == source]
        
    formatted = []
    for g in gaps:
        formatted.append({
            "id": str(g.get("id")),
            "text": g.get("text", ""),
            "source": g.get("source", "llm_synthesized"),
            "related_claims": [str(cid) for cid in g.get("related_claims", [])],
            "confidence": 0.8  # dummy fallback
        })
        
    return {"total": len(formatted), "gaps": formatted}


# ─── Coordinator ──────────────────────────────────────────────────────────────

@app.post("/api/query", response_model=CoordinatorOutput)
def run_query(body: dict):
    """
    Run the coordinator v2 on a research question.
    Body: {"question": "your question here"}
    """
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    from agents.coordinator_v2 import run
    output = run(question, verbose=False)
    
    # Extract confidence mapping
    raw_result = output.get("raw", {})
    conf_str = raw_result.get("confidence_in_answer", "medium").lower()
    conf_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
    confidence_num = conf_map.get(conf_str, 0.6)
    
    # Extract unique cited sources (arxiv IDs)
    sources = set()
    for item in raw_result.get("consensus", []):
        for cit in item.get("citations", []):
            if cit:
                sources.add(str(cit))
    for item in raw_result.get("disputed", []):
        pa = item.get("position_a", {})
        pb = item.get("position_b", {})
        if isinstance(pa, dict) and pa.get("paper"):
            sources.add(str(pa["paper"]))
        if isinstance(pb, dict) and pb.get("paper"):
            sources.add(str(pb["paper"]))
            
    # Format plan as list of string subqueries for the frontend
    raw_plan = output.get("plan", {})
    sub_queries = raw_plan.get("sub_queries", [])
    
    # Map reflection log to match ReflectionStep schema
    reflection_log = []
    for step in output.get("reflection_log", []):
        reflection_log.append({
            "step": step.get("iteration", 1),
            "action": f"Iteration {step.get('iteration', 1)} reflection",
            "observation": step.get("assessment", ""),
            "reasoning": f"Query refined: {step.get('refined_query')}" if step.get("refined_query") else "Context marked sufficient"
        })
        
    return {
        "report": output.get("report", ""),
        "raw": json.dumps(raw_result),
        "iterations": output.get("iterations", 1),
        "plan": sub_queries,
        "reflection_log": reflection_log,
        "confidence": confidence_num,
        "sources": list(sources)
    }


# ─── Temporal Reasoning ───────────────────────────────────────────────────────

@app.get("/api/temporal/evolution", response_model=TemporalEvolution)
def get_evolution(
    topic: str,
    year_start: int = 2020,
    year_end: int = 2025
):
    from agents.temporal import get_consensus_evolution
    res = get_consensus_evolution(topic, year_start, year_end)
    
    yearly_positions = []
    for pos in res.get("yearly_positions", []):
        yearly_positions.append({
            "year": int(pos.get("year", 2020)),
            "position": pos.get("position", ""),
            "confidence": pos.get("confidence", 0.8),
            "key_papers": pos.get("key_claim_arxiv_ids", [])
        })
        
    return {
        "topic": topic,
        "yearly_positions": yearly_positions,
        "narrative": res.get("overall_narrative", ""),
        "current_status": res.get("current_status", "fragmented")
    }


@app.get("/api/temporal/disputes", response_model=DisputeTimeline)
def get_disputes(topic: str):
    from agents.temporal import get_contradiction_timeline
    res = get_contradiction_timeline(topic)
    
    disputes = []
    for d in res.get("disputes", []):
        disputes.append({
            "id": str(d.get("id", "")),
            "topic": d.get("explanation", ""),
            "start_year": d.get("year_a", 2022),
            "end_year": d.get("year_b"),
            "resolved": False,
            "key_claims": [d.get("claim_a", ""), d.get("claim_b", "")]
        })
        
    return {
        "topic": topic,
        "disputes": disputes
    }


# ─── Confidence ───────────────────────────────────────────────────────────────

@app.get("/api/confidence/distribution", response_model=ConfidenceDistribution)
def confidence_distribution():
    from agents.confidence_updater import get_confidence_distribution
    dist = get_confidence_distribution()
    return {
        "total": dist.get("total", 0),
        "average": dist.get("avg_confidence", 0.0) or 0.0,
        "high": dist.get("high_confidence", 0),
        "medium": dist.get("medium_confidence", 0),
        "low": dist.get("low_confidence", 0)
    }


@app.get("/api/confidence/most-changed", response_model=list[ChangedClaim])
def most_changed(limit: int = 10):
    from agents.confidence_updater import get_most_changed_claims
    raw_changed = get_most_changed_claims(limit=limit)
    
    results = []
    for c in raw_changed:
        supports = c.get("supports", 0) or 0
        contradictions = c.get("contradictions", 0) or 0
        reason = f"{supports} support{'s' if supports != 1 else ''}, {contradictions} contradiction{'s' if contradictions != 1 else ''}"
        
        results.append({
            "claim_id": str(c.get("claim_id")),
            "claim_text": c.get("text", ""),
            "base_confidence": c.get("base", 0.0),
            "current_confidence": c.get("current", 0.0),
            "delta": c.get("delta", 0.0),
            "reason": reason
        })
    return results


@app.post("/api/confidence/recalculate")
def recalculate_confidence():
    from agents.confidence_updater import recalculate_all
    summary = recalculate_all()
    return {"updated": summary.get("total_updated", 0)}


# ─── Ingestion ────────────────────────────────────────────────────────────────

@app.get("/api/ingestion/status", response_model=IngestionSummary)
def ingestion_status():
    from ingestion.scheduler import get_run_log
    log = get_run_log()
    if not log:
        return {
            "new_papers": 0,
            "new_claims": 0,
            "last_run": None,
            "running": False
        }
    last = log[-1]
    return {
        "new_papers": last.get("papers_added", 0),
        "new_claims": last.get("claims_added", 0),
        "last_run": last.get("timestamp"),
        "running": False
    }


@app.post("/api/ingestion/trigger")
def trigger_ingestion(background_tasks: BackgroundTasks):
    """Trigger an ingestion cycle in the background."""
    from ingestion.scheduler import trigger_now
    background_tasks.add_task(trigger_now)
    return {"status": "ingestion started in background"}


# ─── Knowledge Graph ──────────────────────────────────────────────────────────

@app.get("/api/graph")
def get_graph_data(limit_claims: int = 100):
    from graph.neo4j_client import run_query

    nodes = []
    edges = []

    # Papers
    papers = run_query("MATCH (p:Paper) RETURN p.arxiv_id AS id, p.title AS title LIMIT 50")
    for p in papers:
        nodes.append({
            "id": f"paper_{p['id']}",
            "label": p["title"][:30] if p["title"] else p["id"],
            "type": "paper",
            "year": 2024  # dummy
        })

    # Claims
    claims = run_query(f"""
        MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
        RETURN elementId(c) AS id, c.text AS text,
               c.confidence AS confidence, p.arxiv_id AS arxiv_id
        LIMIT {limit_claims}
    """)
    for c in claims:
        nodes.append({
            "id": f"claim_{c['id']}",
            "label": c["text"][:30],
            "type": "claim",
            "confidence": c["confidence"]
        })
        edges.append({
            "source": f"claim_{c['id']}",
            "target": f"paper_{c['arxiv_id']}",
            "type": "EXTRACTED_FROM"
        })

    # Contradictions
    contras = run_query("""
        MATCH (a:Claim)-[r:CONTRADICTS]->(b:Claim)
        RETURN elementId(a) AS a_id, elementId(b) AS b_id,
               r.explanation AS explanation, r.confidence AS confidence
        LIMIT 100
    """)
    for r in contras:
        edges.append({
            "source": f"claim_{r['a_id']}",
            "target": f"claim_{r['b_id']}",
            "type": "CONTRADICTS"
        })

    # Gaps
    gaps = run_query("""
        MATCH (g:Gap)
        RETURN elementId(g) AS id, g.text AS text
        LIMIT 30
    """)
    for g in gaps:
        nodes.append({
            "id": f"gap_{g['id']}",
            "label": g["text"][:30],
            "type": "gap"
        })

    return {"nodes": nodes, "edges": edges}


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Quick health check — verifies Neo4j is reachable."""
    try:
        from graph.neo4j_queries import get_graph_stats
        stats = get_graph_stats()
        return {"status": "ok", "claims": stats.get("claims", 0)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j unreachable: {e}")
