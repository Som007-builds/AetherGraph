# agents/reflector.py
import json
from llm import call_llm

REFLECTOR_PROMPT = """You are the reflection agent in a multi-agent research system.

A researcher asked: "{question}"

The retriever found this context:

CLAIMS RETRIEVED ({n_claims}):
{claims_text}

CONTRADICTIONS RETRIEVED ({n_contradictions}):
{contradictions_text}

GAPS RETRIEVED ({n_gaps}):
{gaps_text}

Evaluate whether this context is sufficient to write a good answer to the question.

Score from 0 to 10:
- 8–10: Sufficient. The synthesizer can write a good, specific, cited answer.
- 5–7: Partially sufficient. Answer is possible but will be vague or miss angles.
- 0–4: Insufficient. The retrieval missed the point or there's almost nothing relevant.

If score < 7, provide a refined search query that would find the missing information.
The refined query should use completely different vocabulary than the previous retrieval.

Return ONLY valid JSON, no other text:
{{
  "score": 0,
  "sufficient": false,
  "assessment": "one sentence on what's missing or why it's enough",
  "refined_query": "new search query if score < 7, else null"
}}
"""

SUFFICIENCY_THRESHOLD = 7


def reflect(question: str, context: dict) -> dict:
    claims = context.get("claims", [])
    contradictions = context.get("contradictions", [])
    gaps = context.get("gaps", [])

    claims_text = ""
    for i, c in enumerate(claims[:8]):
        claims_text += f"{i+1}. [{c.get('arxiv_id', '?')}] {c.get('text', '')[:120]}\n"
    if not claims_text:
        claims_text = "None found."

    contradictions_text = ""
    for c in contradictions[:4]:
        contradictions_text += f"- {c.get('explanation', '')[:100]}\n"
    if not contradictions_text:
        contradictions_text = "None found."

    gaps_text = ""
    for g in gaps[:4]:
        gaps_text += f"- {g.get('text', '')[:100]}\n"
    if not gaps_text:
        gaps_text = "None found."

    prompt = REFLECTOR_PROMPT.format(
        question=question,
        n_claims=len(claims),
        claims_text=claims_text,
        n_contradictions=len(contradictions),
        contradictions_text=contradictions_text,
        n_gaps=len(gaps),
        gaps_text=gaps_text
    )

    raw = call_llm(prompt, max_tokens=400)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find and parse JSON object
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                result = json.loads(raw[start:end])
            except json.JSONDecodeError:
                print("  [Reflector] JSON parse failed, defaulting to sufficient")
                result = {
                    "score": 7,
                    "sufficient": True,
                    "assessment": "parse error — proceeding with available context",
                    "refined_query": None
                }
        else:
            print("  [Reflector] JSON parse failed, defaulting to sufficient")
            result = {
                "score": 7,
                "sufficient": True,
                "assessment": "parse error — proceeding with available context",
                "refined_query": None
            }

    result["sufficient"] = result.get("score", 0) >= SUFFICIENCY_THRESHOLD
    return result

    result["sufficient"] = result.get("score", 0) >= SUFFICIENCY_THRESHOLD
    return result