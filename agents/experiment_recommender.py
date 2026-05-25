# agents/experiment_recommender.py
"""
Experiment Recommender.

Given a contradiction between two papers, designs the minimal experiment
that would determine which side is correct.

Uses call_llm() (Groq/Gemini/Claude — whatever LLM_PROVIDER is set to in
config.py) so no separate API client or key is needed.

Output is a structured dict — zero display logic here.
Phase 7 note: the UI renders this dict; the agent just returns data.

Experiment designs are stored on the CONTRADICTS relationship in Neo4j
so they are permanently linked to the contradiction that motivated them.
"""

import json
import re

from llm import call_llm
from graph.neo4j_queries import get_contradictions
from graph.neo4j_client import run_query, run_write
from utils.logger import get_logger, log_event

logger = get_logger("experiment_recommender")

EXPERIMENT_PROMPT = """You are a research methodology expert designing experiments to resolve scientific disputes.

Two papers make contradictory claims:

Paper A: "{paper_a_title}"
Claim A: "{claim_a}"

Paper B: "{paper_b_title}"
Claim B: "{claim_b}"

The contradiction: {explanation}

Design the MINIMAL experiment that would definitively determine which claim is correct.
Minimal means: fewest resources, fastest to run, most decisive result.

Rules:
- Be specific about dataset names, model families, exact metrics
- The experiment must be feasible with academic resources (no 1000-GPU training runs)
- Describe what a researcher would actually do, step by step
- Expected outcomes must be mutually exclusive — seeing one rules out the other

Return ONLY valid JSON, no other text, no markdown fences:
{{
  "hypothesis_a": "If Paper A is correct, we expect to see...",
  "hypothesis_b": "If Paper B is correct, we expect to see...",
  "experiment": {{
    "title": "Short title for this experiment",
    "dataset": "Specific dataset(s) to use and why",
    "models": "Model families and sizes to test (e.g. LLaMA-7B, 13B, 70B)",
    "metric": "Primary metric to measure",
    "baseline": "What to compare against",
    "procedure": "Step-by-step what to do (3-5 steps)",
    "expected_duration": "Realistic estimate (e.g. 2 GPU-days)",
    "cost_estimate": "Rough compute cost in USD"
  }},
  "decision_rule": "If metric X exceeds Y threshold on model Z, Paper A is supported. Otherwise Paper B is supported.",
  "confidence_in_design": 0.85,
  "caveats": "One sentence on what this experiment cannot rule out"
}}
"""


def safe_json_parse(raw: str) -> dict | None:
    """
    Robust JSON parsing for messy LLM outputs.

    Handles:
    - markdown fences
    - leading/trailing text
    - control characters
    - malformed formatting
    """

    if not raw:
        return None

    try:
        raw = raw.strip()

        # Remove markdown fences
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"```$", "", raw)
        raw = raw.strip()

        # Extract first JSON object
        match = re.search(r"\{.*\}", raw, re.DOTALL)

        if match:
            raw = match.group(0)

        # Remove problematic control chars
        raw = re.sub(r"[\x00-\x1F\x7F]", "", raw)

        return json.loads(raw)

    except Exception as e:
        log_event(logger, "experiment_json_parse_failed", {
            "error": str(e),
            "raw_snippet": raw[:500] if raw else "",
        })
        return None


def design_experiment(contradiction: dict) -> dict | None:
    """
    Design an experiment to resolve a single contradiction.

    Args:
        contradiction: dict from get_contradictions() with keys:
            id, claim_a, claim_b, paper_a, paper_b, explanation, confidence

    Returns:
        Experiment design dict, or None if generation/parsing failed.
    """

    prompt = EXPERIMENT_PROMPT.format(
        paper_a_title=contradiction.get("paper_a", "Unknown Paper A"),
        claim_a=contradiction.get("claim_a", ""),
        paper_b_title=contradiction.get("paper_b", "Unknown Paper B"),
        claim_b=contradiction.get("claim_b", ""),
        explanation=contradiction.get("explanation", ""),
    )

    try:
        raw = call_llm(prompt, max_tokens=1200)

        result = safe_json_parse(raw)

        if not result:
            log_event(logger, "experiment_design_parse_failed", {
                "contradiction_id": contradiction.get("id"),
                "raw_snippet": raw[:300] if raw else "",
            })
            return None

        # Add metadata
        result["contradiction_id"] = contradiction.get("id")
        result["contradiction_confidence"] = contradiction.get("confidence", 0)

        log_event(logger, "experiment_designed", {
            "contradiction_id": contradiction.get("id"),
            "design_confidence": result.get("confidence_in_design"),
        })

        return result

    except Exception as e:
        log_event(logger, "experiment_design_failed", {
            "contradiction_id": contradiction.get("id"),
            "error": str(e),
        })
        return None


def store_experiment(contradiction_id: str, experiment: dict) -> None:
    """
    Persist the experiment design on the CONTRADICTS relationship in Neo4j.
    Stored as JSON so the full structure is retrievable without a schema change.
    """

    run_write("""
        MATCH ()-[r:CONTRADICTS]->()
        WHERE elementId(r) = $rid
        SET r.experiment_design      = $design,
            r.experiment_designed_at = datetime()
    """, {
        "rid": str(contradiction_id),
        "design": json.dumps(experiment),
    })


def get_experiment_for_contradiction(contradiction_id: str) -> dict | None:
    """
    Retrieve a stored experiment design for a contradiction.
    Returns None if no experiment has been designed yet.
    """

    result = run_query("""
        MATCH ()-[r:CONTRADICTS]->()
        WHERE elementId(r) = $rid
        RETURN r.experiment_design AS design
    """, {"rid": str(contradiction_id)})

    if not result or not result[0].get("design"):
        return None

    try:
        return json.loads(result[0]["design"])

    except (json.JSONDecodeError, TypeError):
        return None


def run_batch_design(
    max_contradictions: int = 20,
    min_contradiction_confidence: float = 0.7,
) -> list[dict]:
    """
    Design experiments for the top N high-confidence contradictions
    that do not already have an experiment stored.

    Args:
        max_contradictions: API cost control cap.
        min_contradiction_confidence: skip low-confidence contradictions.

    Returns:
        List of experiment design dicts that were successfully generated.
    """

    contradictions = get_contradictions()

    candidates = [
        c for c in contradictions
        if c.get("confidence", 0) >= min_contradiction_confidence
        and get_experiment_for_contradiction(c["id"]) is None
    ][:max_contradictions]

    logger.info(
        f"Designing experiments for {len(candidates)} contradictions "
        f"(confidence >= {min_contradiction_confidence})..."
    )

    designed = []

    for i, contradiction in enumerate(candidates):
        snippet = (contradiction.get("explanation") or "")[:60]

        logger.info(f"  [{i+1}/{len(candidates)}] {snippet}...")

        experiment = design_experiment(contradiction)

        if experiment:
            store_experiment(contradiction["id"], experiment)
            designed.append(experiment)

    logger.info(f"Done. Designed {len(designed)} experiments.")

    return designed