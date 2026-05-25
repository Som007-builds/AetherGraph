# agents/reader.py
"""
PHASE 6 CHANGE:
  After insert_claim(), immediately SET base_confidence = confidence on the
  new Claim node. This means every claim extracted from this point forward
  has base_confidence populated at birth, so confidence_updater.py can
  recalculate without needing the one-time migration for new papers.

  (migrate_base_confidence.py still handles existing claims in the graph.)
"""
import json
import logging
from pathlib import Path
from config import MAX_CLAIMS_PER_PAPER
from llm import call_llm
from ingestion.pdf_parser import extract_sections, chunk_text
from graph.neo4j_queries import insert_paper, insert_claim, get_paper_by_arxiv_id
from graph.neo4j_client import run_write
from embeddings.store import add_claim, add_chunk

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """You are a research analyst extracting specific, falsifiable claims from an AI/ML research paper.

A GOOD claim is:
- Specific and measurable: mentions metrics, numbers, model sizes, benchmarks
- Falsifiable: can be proven true or false with an experiment
- A finding FROM this paper (not background from others)

A BAD claim is:
- Vague: "larger models perform better"
- Obvious: "we evaluate on standard benchmarks"
- From related work, not from this paper

Paper section ({section}):
---
{text}
---

Extract up to {max_claims} falsifiable claims. Return ONLY valid JSON, no other text:
{{
  "claims": [
    {{
      "claim": "the specific falsifiable claim as a complete sentence",
      "confidence": 0.0 to 1.0,
      "keywords": ["list", "of", "key", "terms"]
    }}
  ]
}}
"""


def extract_claims_from_section(section_text: str, section_name: str) -> list[dict]:
    """Call LLM to extract claims from a single section."""
    prompt = EXTRACTION_PROMPT.format(
        section=section_name,
        text=section_text[:3000],
        max_claims=MAX_CLAIMS_PER_PAPER,
    )

    raw = call_llm(prompt)

    try:
        data = json.loads(raw)
        return data.get("claims", [])
    except json.JSONDecodeError:
        clean = raw
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        start = clean.find("{")
        if start != -1:
            try:
                data = json.loads(clean[start:])
                return data.get("claims", [])
            except json.JSONDecodeError:
                pass
        logger.warning(f"  Warning: Could not parse claims from section {section_name}")
        return []


def process_paper(paper_meta: dict, pdf_path: Path) -> int:
    """
    Full pipeline: extract text → extract claims → store in Neo4j + ChromaDB.
    Returns number of claims extracted.
    """
    logger.info(f"\nProcessing: {paper_meta['title'][:60]}")

    # Extract paper_year from published date
    paper_year = None
    published = paper_meta.get("published", "")
    if published and len(published) >= 4:
        try:
            paper_year = int(published[:4])
        except ValueError:
            pass

    # 1. Store paper in Neo4j
    arxiv_id = insert_paper(
        arxiv_id=paper_meta["arxiv_id"],
        title=paper_meta["title"],
        authors=paper_meta["authors"],
        abstract=paper_meta["abstract"],
        published=published,
    )
    logger.info(f"  ArXiv ID: {arxiv_id}  Year: {paper_year}")

    # 2. Extract sections
    sections = extract_sections(pdf_path)
    logger.info(f"  Sections found: {list(sections.keys())}")

    # 3. Store chunks for retrieval
    for section_name, text in sections.items():
        for i, chunk in enumerate(chunk_text(text)):
            chunk_id = f"{paper_meta['arxiv_id']}_{section_name}_{i}"
            add_chunk(chunk_id, chunk, {
                "arxiv_id":    paper_meta["arxiv_id"],
                "section":     section_name,
                "paper_title": paper_meta["title"],
            })

    # 4. Extract claims from key sections
    target_sections = ["Abstract", "Introduction", "Results",
                       "Experiments", "Conclusion", "preamble"]
    claims_extracted = 0

    for section_name in target_sections:
        if section_name not in sections:
            continue

        logger.info(f"  Extracting from: {section_name}...")
        raw_claims = extract_claims_from_section(sections[section_name], section_name)

        for raw_claim in raw_claims:
            claim_text = raw_claim.get("claim", "").strip()
            if not claim_text or len(claim_text) < 20:
                continue

            confidence_val = raw_claim.get("confidence", 1.0)

            # Store in Neo4j
            claim_id = insert_claim(
                paper_id=arxiv_id,
                claim_text=claim_text,
                section=section_name,
                confidence=confidence_val,
                paper_year=paper_year,
            )

            # Phase 6: stamp base_confidence at birth so confidence_updater
            # can recalculate without a migration pass for new claims.
            run_write("""
                MATCH (c:Claim) WHERE elementId(c) = $claim_id
                SET c.base_confidence = $confidence
            """, {"claim_id": str(claim_id), "confidence": confidence_val})

            # Store in ChromaDB with paper_year as int for temporal filtering.
            # Audit §3.3: paper_year must be int in ChromaDB metadata so
            # temporal.py year range filter works without coercion.
            add_claim(claim_id, claim_text, {
                "claim_id":   str(claim_id),
                "paper_id":   arxiv_id,
                "arxiv_id":   paper_meta["arxiv_id"],
                "section":    section_name,
                "paper_year": paper_year if paper_year is not None else 0,
            })

            claims_extracted += 1

    logger.info(f"  Extracted {claims_extracted} claims total")
    return claims_extracted