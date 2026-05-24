# agents/synthesizer.py
import json
from llm import call_llm

SYNTHESIZER_PROMPT = """You are the synthesis agent in a multi-agent research system.

A researcher asked: "{question}"

You have been given verified, sufficient context from the knowledge graph.

CLAIMS (with paper sources):
{claims_text}

CONTRADICTIONS:
{contradictions_text}

GAPS:
{gaps_text}

Write a structured research synthesis report. Rules:
- Every consensus point must cite at least one arxiv_id in brackets like [2301.00001]
- Every disputed point must name both sides and their source papers
- Be specific — no vague statements like "some papers suggest"
- Gaps should be framed as research questions, not problems

Return ONLY valid JSON, no other text:
{{
  "consensus": [
    {{
      "finding": "specific finding",
      "citations": ["arxiv_id_1"]
    }}
  ],
  "disputed": [
    {{
      "topic": "what is disputed",
      "position_a": {{"claim": "position", "paper": "arxiv_id"}},
      "position_b": {{"claim": "opposing position", "paper": "arxiv_id"}}
    }}
  ],
  "missing": [
    "specific unanswered research question"
  ],
  "recommended_experiments": [
    "specific experiment that would resolve a dispute or gap"
  ],
  "confidence_in_answer": "high | medium | low",
  "confidence_reason": "one sentence explaining the confidence level"
}}
"""


def synthesize(question: str, context: dict) -> dict:
    claims = context.get("claims", [])
    contradictions = context.get("contradictions", [])
    gaps = context.get("gaps", [])

    claims_text = ""
    for i, c in enumerate(claims[:10]):
        claims_text += f"{i+1}. [{c.get('arxiv_id', '?')}] {c.get('text', '')[:150]}\n"
    if not claims_text:
        claims_text = "None available."

    contradictions_text = ""
    for c in contradictions[:5]:
        contradictions_text += (
            f"- [{c.get('paper_a', '?')[:30]}] vs [{c.get('paper_b', '?')[:30]}]: "
            f"{c.get('explanation', '')[:120]}\n"
        )
    if not contradictions_text:
        contradictions_text = "None detected."

    gaps_text = "\n".join(f"- {g.get('text', '')}" for g in gaps[:5])
    if not gaps_text:
        gaps_text = "None identified."

    prompt = SYNTHESIZER_PROMPT.format(
        question=question,
        claims_text=claims_text,
        contradictions_text=contradictions_text,
        gaps_text=gaps_text
    )

    raw = call_llm(prompt, max_tokens=2000)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        result = json.loads(raw[start:]) if start != -1 else {}

    return result


def format_report(question: str, result: dict, iterations_taken: int) -> str:
    lines = [
        "# SciMesh Research Report",
        f"**Question:** {question}",
        f"**Coordinator iterations:** {iterations_taken}",
        f"**Answer confidence:** {result.get('confidence_in_answer', 'unknown')} — {result.get('confidence_reason', '')}",
        "",
        "---",
        "",
        "## Consensus",
    ]

    for item in result.get("consensus", []):
        citations = ", ".join(f"[{c}]" for c in item.get("citations", []))
        lines.append(f"- {item.get('finding', '')} {citations}")

    if not result.get("consensus"):
        lines.append("- No clear consensus found in current graph.")

    lines += ["", "## Disputes"]
    for d in result.get("disputed", []):
        lines.append(f"\n**{d.get('topic', '')}**")
        pa = d.get("position_a", {})
        pb = d.get("position_b", {})
        lines.append(f"  - [{pa.get('paper', '?')}] {pa.get('claim', '')}")
        lines.append(f"  - [{pb.get('paper', '?')}] {pb.get('claim', '')}")

    if not result.get("disputed"):
        lines.append("- No contradictions found for this topic.")

    lines += ["", "## Research Gaps"]
    for gap in result.get("missing", []):
        lines.append(f"- {gap}")

    lines += ["", "## Recommended Experiments"]
    for rec in result.get("recommended_experiments", []):
        lines.append(f"- {rec}")

    return "\n".join(lines)