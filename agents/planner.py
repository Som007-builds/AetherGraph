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
- Break the question into 1-3 specific sub-queries if it's complex
- Each sub-query MUST be a plain string — no dicts, no keys, no JSON objects
- Decide whether contradictions are relevant (yes if the question is about disagreement, debate, or conflicting results)
- Decide whether gaps are relevant (yes if the question is about what is unknown, unsolved, or missing)
- Each sub-query should use different vocabulary from the others — do not repeat the same search

Example of CORRECT sub_queries:
["chain of thought prompting small models performance", "reasoning ability limited parameter language models"]

Example of INCORRECT sub_queries (never do this):
[{{"ChromaDB": "chain_of_thought"}}, {{"key": "value"}}]

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
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                plan = json.loads(raw[start:end])
            except json.JSONDecodeError:
                print("  [Planner] JSON parse failed, using fallback plan")
                plan = {
                    "sub_queries": [question],
                    "fetch_contradictions": True,
                    "fetch_gaps": True,
                    "reasoning": "fallback: used question directly"
                }
        else:
            print("  [Planner] JSON parse failed, using fallback plan")
            plan = {
                "sub_queries": [question],
                "fetch_contradictions": True,
                "fetch_gaps": True,
                "reasoning": "fallback: used question directly"
            }

    # Validate and clamp sub_queries — log every non-string case
    raw_queries = plan.get("sub_queries", [question])
    cleaned_queries = []

    for q in raw_queries:
        if isinstance(q, str):
            cleaned_queries.append(q)
        elif isinstance(q, dict):
            extracted = list(q.values())[0] if q else question
            print(f"  [Planner] ⚠️  Dict sub_query clamped: {q} → '{extracted}'")
            cleaned_queries.append(str(extracted))
        else:
            fallback = str(q)
            print(f"  [Planner] ⚠️  Unexpected sub_query type {type(q)}: {q} → '{fallback}'")
            cleaned_queries.append(fallback)

    plan["sub_queries"] = cleaned_queries[:3]
    plan["fetch_contradictions"] = bool(plan.get("fetch_contradictions", True))
    plan["fetch_gaps"] = bool(plan.get("fetch_gaps", True))

    return plan