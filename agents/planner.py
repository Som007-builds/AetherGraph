# agents/planner.py
import json
from llm import call_llm

PLANNER_PROMPT = """You are the planning agent in a multi-agent research system.

A researcher has asked this question:
"{question}"

Your job is to produce a retrieval plan. The system has access to:
1. A semantic search over research claims (ChromaDB)
2. A list of detected contradictions between papers
3. A list of identified research gaps

Produce a plan that tells the retriever exactly what to look for.

Rules:
- Break the question into 1–3 specific sub-queries if it's complex
- Decide whether contradictions are relevant (yes if the question is about disagreement, debate, or conflicting results)
- Decide whether gaps are relevant (yes if the question is about what's unknown, unsolved, or missing)
- Each sub-query should use different vocabulary from the others — don't repeat the same search

Return ONLY valid JSON, no other text:
{{
  "sub_queries": [
    "specific claim search query 1",
    "specific claim search query 2"
  ],
  "fetch_contradictions": true,
  "fetch_gaps": true,
  "reasoning": "one sentence explaining your retrieval strategy"
}}
"""


def make_plan(question: str) -> dict:
    prompt = PLANNER_PROMPT.format(question=question)
    raw = call_llm(prompt, max_tokens=600)

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        if start != -1:
            plan = json.loads(raw[start:])
        else:
            print("  [Planner] JSON parse failed, using fallback plan")
            plan = {
                "sub_queries": [question],
                "fetch_contradictions": True,
                "fetch_gaps": True,
                "reasoning": "fallback: used question directly"
            }

    plan["sub_queries"] = plan.get("sub_queries", [question])[:3]
    plan["fetch_contradictions"] = bool(plan.get("fetch_contradictions", True))
    plan["fetch_gaps"] = bool(plan.get("fetch_gaps", True))

    return plan