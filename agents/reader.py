import json
from pathlib import Path
from config import MAX_CLAIMS_PER_PAPER
from llm import call_llm
from ingestion.pdf_parser import extract_sections, chunk_text
from graph.queries import insert_paper, insert_claim
from embeddings.store import add_claim, add_chunk

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
        max_claims=MAX_CLAIMS_PER_PAPER
    )

    raw = call_llm(prompt)

    try:
        data = json.loads(raw)
        return data.get("claims", [])
    except json.JSONDecodeError:
        # Strip markdown code fences if present
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
        print(f"  Warning: Could not parse claims from section {section_name}")
        return []


def process_paper(paper_meta: dict, pdf_path: Path) -> int:
    """
    Full pipeline: extract text -> extract claims -> store in graph.
    Returns number of claims extracted.
    """
    print(f"\nProcessing: {paper_meta['title'][:60]}")

    # 1. Store paper in DB
    paper_id = insert_paper(
        arxiv_id=paper_meta["arxiv_id"],
        title=paper_meta["title"],
        authors=paper_meta["authors"],
        abstract=paper_meta["abstract"],
        published=paper_meta["published"]
    )
    print(f"  Paper ID: {paper_id}")

    # 2. Extract sections
    sections = extract_sections(pdf_path)
    print(f"  Sections found: {list(sections.keys())}")

    # 3. Store chunks for retrieval
    for section_name, text in sections.items():
        for i, chunk in enumerate(chunk_text(text)):
            chunk_id = f"{paper_meta['arxiv_id']}_{section_name}_{i}"
            add_chunk(chunk_id, chunk, {
                "arxiv_id": paper_meta["arxiv_id"],
                "section": section_name,
                "paper_title": paper_meta["title"]
            })

    # 4. Extract claims from key sections
    target_sections = ["Abstract", "Introduction", "Results",
                       "Experiments", "Conclusion", "preamble"]
    claims_extracted = 0

    for section_name in target_sections:
        if section_name not in sections:
            continue

        print(f"  Extracting from: {section_name}...")
        raw_claims = extract_claims_from_section(sections[section_name], section_name)

        for raw_claim in raw_claims:
            claim_text = raw_claim.get("claim", "").strip()
            if not claim_text or len(claim_text) < 20:
                continue

            # Store in SQLite
            claim_id = insert_claim(
                paper_id=paper_id,
                claim_text=claim_text,
                section=section_name,
                confidence=raw_claim.get("confidence", 1.0)
            )

            # Store in ChromaDB
            add_claim(claim_id, claim_text, {
                "claim_id": str(claim_id),
                "paper_id": str(paper_id),
                "arxiv_id": paper_meta["arxiv_id"],
                "section": section_name
            })

            claims_extracted += 1

    print(f"  Extracted {claims_extracted} claims total")
    return claims_extracted