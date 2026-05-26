# agents/reader.py
"""
Reader Agent — Paper ingestion pipeline.

Phase 1: All JSON parsing now uses utils.llm_parser.normalize_claim_output(),
         which handles every known LLM output format safely.

Phase 2: Per-section fault isolation — a crashed section is logged and
         skipped; the remaining sections continue. A crashed paper is
         caught at the ingest() level in main.py.

Phase 4: Structured claim extraction — the prompt now requests subject /
         predicate / object / conditions / metric / direction / evidence_span.
         Partial extraction is tolerated; missing structured fields fall back
         to raw claim_text only.

Phase 7: evidence_span is propagated to Neo4j as a first-class Claim property.

Phase 9: @trace_agent decorator applied to process_paper() for automatic
         start / complete / fail timing logs.
"""

import logging
from pathlib import Path

from config import MAX_CLAIMS_PER_PAPER
from llm import call_llm
from ingestion.pdf_parser import extract_sections, chunk_text
from graph.neo4j_queries import insert_paper, insert_claim, get_paper_by_arxiv_id
from graph.neo4j_client import run_write
from embeddings.store import add_claim, add_chunk
from utils.llm_parser import normalize_claim_output
from utils.logger import get_logger, trace_agent

logger = get_logger(__name__)


# ─── Extraction Prompt ────────────────────────────────────────────────────────
# Phase 4: requests structured claims with optional provenance fields.
# Partial extraction is explicitly permitted — the parser tolerates missing
# structured fields and falls back to claim_text only.

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
      "claim_text": "the specific falsifiable claim as a complete sentence",
      "subject": "what entity or system this claim is about (e.g. 'LLMs under 3B params')",
      "predicate": "the property or relationship claimed (e.g. 'degrade with')",
      "object": "the outcome or value (e.g. 'chain-of-thought prompting')",
      "conditions": {{
        "model_size": "e.g. >10B, 7B, <3B — or omit if not mentioned",
        "dataset": "e.g. GSM8K, MMLU — or omit if not mentioned",
        "benchmark": "e.g. mathematical reasoning — or omit if not mentioned",
        "training_method": "e.g. RLHF, SFT — or omit if not mentioned",
        "evaluation_setting": "e.g. zero-shot, 5-shot — or omit if not mentioned"
      }},
      "metric": "e.g. accuracy, F1, perplexity — or omit if not mentioned",
      "direction": "increases | decreases | no_effect | unclear",
      "confidence": 0.0,
      "evidence_span": "short quote or close paraphrase from the paper text supporting this claim",
      "keywords": ["list", "of", "key", "terms"]
    }}
  ]
}}

Note: conditions, subject, predicate, object, metric, evidence_span are optional.
If uncertain, omit them rather than hallucinating. claim_text is required.
"""


# ─── Claim Extraction ─────────────────────────────────────────────────────────

def extract_claims_from_section(section_text: str, section_name: str) -> list[dict]:
    """
    Call LLM to extract structured claims from a single section.
    Uses normalize_claim_output() — handles every known LLM output format.
    """
    prompt = EXTRACTION_PROMPT.format(
        section=section_name,
        text=section_text[:3000],
        max_claims=MAX_CLAIMS_PER_PAPER,
    )

    raw = call_llm(prompt, context=f"reader.{section_name}")

    # Phase 1: robust normalisation — never crashes on malformed output
    claims = normalize_claim_output(raw, context=f"reader.{section_name}")

    if not claims:
        logger.debug(
            f"  [reader] Section '{section_name}': 0 usable claims parsed "
            f"from raw output ({len(raw or '')} chars)."
        )

    return claims


# ─── Paper Processing ──────────────────────────────────────────────────────────

@trace_agent("reader")
def process_paper(paper_meta: dict, pdf_path: Path) -> int:
    """
    Full pipeline: extract text → extract claims → store in Neo4j + ChromaDB.
    Returns number of claims extracted.

    Phase 2: per-section fault isolation — a crashed section is skipped.
    Phase 9: @trace_agent provides start / complete / fail timing logging.
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
            try:
                add_chunk(chunk_id, chunk, {
                    "arxiv_id":    paper_meta["arxiv_id"],
                    "section":     section_name,
                    "paper_title": paper_meta["title"],
                })
            except Exception as e:
                logger.warning(f"  [reader] Chunk storage failed for {chunk_id}: {e}")

    # 4. Extract claims from key sections
    target_sections = ["Abstract", "Introduction", "Results",
                       "Experiments", "Conclusion", "preamble"]
    claims_extracted = 0

    for section_name in target_sections:
        if section_name not in sections:
            continue

        logger.info(f"  Extracting from: {section_name}…")

        # Phase 2: per-section try/except — one bad section never kills the paper
        try:
            raw_claims = extract_claims_from_section(sections[section_name], section_name)
        except Exception as e:
            logger.warning(
                f"  [reader] Section '{section_name}' extraction failed: {e}. Skipping section."
            )
            continue

        for raw_claim in raw_claims:
            # claim_text is the normalised text field (set by validate_claim)
            claim_text = raw_claim.get("claim_text") or raw_claim.get("claim", "")
            claim_text = claim_text.strip()
            if not claim_text or len(claim_text) < 20:
                continue

            confidence_val = raw_claim.get("confidence", 1.0)

            # Phase 4: collect structured fields if present
            structured = {}
            for field in ("subject", "predicate", "object", "metric",
                          "direction", "evidence_span", "conditions"):
                val = raw_claim.get(field)
                if val:
                    structured[field] = val

            # Store in Neo4j (structured fields forwarded)
            try:
                claim_id = insert_claim(
                    paper_id=arxiv_id,
                    claim_text=claim_text,
                    section=section_name,
                    confidence=confidence_val,
                    paper_year=paper_year,
                    structured=structured if structured else None,
                )
            except Exception as e:
                logger.warning(f"  [reader] Neo4j insert failed for claim: {e}")
                continue

            if claim_id is None:
                continue

            # Phase 6 / Phase 7: stamp base_confidence + evidence_span at birth
            try:
                run_write("""
                    MATCH (c:Claim) WHERE elementId(c) = $claim_id
                    SET c.base_confidence = $confidence
                """, {"claim_id": str(claim_id), "confidence": confidence_val})
            except Exception as e:
                logger.warning(f"  [reader] base_confidence stamp failed: {e}")

            # Store in ChromaDB
            try:
                add_claim(claim_id, claim_text, {
                    "claim_id":   str(claim_id),
                    "paper_id":   arxiv_id,
                    "arxiv_id":   paper_meta["arxiv_id"],
                    "section":    section_name,
                    "paper_year": paper_year if paper_year is not None else 0,
                })
            except Exception as e:
                logger.warning(f"  [reader] ChromaDB add failed for claim {claim_id}: {e}")

            claims_extracted += 1

    logger.info(f"  Extracted {claims_extracted} claims total")
    return claims_extracted