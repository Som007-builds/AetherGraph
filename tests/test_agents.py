# tests/test_agents.py
"""
Agent integration tests.
Run with: pytest tests/test_agents.py -v
Each test is isolated and doesn't require specific graph data.
"""
import json
import pytest
from agents.planner import make_plan
from agents.reflector import reflect
from agents.synthesizer import synthesize


def test_planner_returns_valid_structure(monkeypatch):
    import agents.planner as planner_module
    mock_plan = {
        "sub_queries": ["chain of thought prompting help small models"],
        "fetch_contradictions": True,
        "fetch_gaps": True,
        "reasoning": "test reasoning"
    }
    monkeypatch.setattr(planner_module, "call_llm", lambda *a, **kw: json.dumps(mock_plan))

    plan = make_plan("Does chain-of-thought prompting help small models?")
    assert "sub_queries" in plan
    assert "fetch_contradictions" in plan
    assert "fetch_gaps" in plan
    assert isinstance(plan["sub_queries"], list)
    assert 1 <= len(plan["sub_queries"]) <= 3
    assert isinstance(plan["fetch_contradictions"], bool)
    assert isinstance(plan["fetch_gaps"], bool)
    for q in plan["sub_queries"]:
        assert isinstance(q, str), f"sub_query is not a string: {q}"


def test_planner_handles_dict_subquery(monkeypatch):
    """Planner must clamp dict sub_queries to plain strings (no silent drops)."""
    import agents.planner as planner_module

    malformed_plan = {
        "sub_queries": [{"query": "What is CoT?"}, "What is prompting?"],
        "fetch_contradictions": True,
        "fetch_gaps": True,
        "reasoning": "test"
    }

    def fake_call_llm(prompt, max_tokens=600, **kwargs):
        return json.dumps(malformed_plan)

    monkeypatch.setattr(planner_module, "call_llm", fake_call_llm)
    plan = make_plan("test question")

    assert isinstance(plan["sub_queries"], list)
    for q in plan["sub_queries"]:
        assert isinstance(q, str), f"Dict was not clamped to str: {q}"


def test_planner_logs_dict_clamp(monkeypatch, caplog):
    """Clamped dict sub_queries must print a warning."""
    import agents.planner as planner_module

    malformed_plan = {
        "sub_queries": [{"query": "What is X?"}],
        "fetch_contradictions": False,
        "fetch_gaps": False,
        "reasoning": "test"
    }

    monkeypatch.setattr(planner_module, "call_llm", lambda *a, **kw: json.dumps(malformed_plan))
    import logging
    with caplog.at_level(logging.WARNING):
        make_plan("test")
    assert any("Dict sub_query clamped" in r.message or "⚠️" in r.message for r in caplog.records)


def test_reflector_scores_empty_context_low(monkeypatch):
    import agents.reflector as reflector_module
    mock_resp = {
        "score": 3,
        "sufficient": False,
        "assessment": "empty context",
        "refined_query": "Does CoT help small LLMs?"
    }
    monkeypatch.setattr(reflector_module, "call_llm", lambda *a, **kw: json.dumps(mock_resp))

    result = reflect(
        "Does CoT help small models?",
        {"claims": [], "contradictions": [], "gaps": []}
    )
    assert result["score"] <= 5
    assert result["sufficient"] is False
    assert result.get("refined_query") is not None


def test_reflector_returns_valid_structure(monkeypatch):
    import agents.reflector as reflector_module
    mock_resp = {
        "score": 8,
        "sufficient": True,
        "assessment": "good context",
        "refined_query": None
    }
    monkeypatch.setattr(reflector_module, "call_llm", lambda *a, **kw: json.dumps(mock_resp))

    result = reflect("test question", {"claims": [], "contradictions": [], "gaps": []})
    assert "score" in result
    assert "sufficient" in result
    assert "assessment" in result
    assert 0 <= result["score"] <= 10


def test_synthesizer_with_mock_context(monkeypatch):
    import agents.synthesizer as synth_module
    mock_synth = {
        "consensus": [{"finding": "CoT improves GSM8K by 40% for 100B+ models.", "citations": ["2201.11903"]}],
        "disputed": [
            {
                "topic": "Effect on small models",
                "position_a": {"claim": "Helps large", "paper": "2201.11903"},
                "position_b": {"claim": "Doesn't help small", "paper": "2302.00001"}
            }
        ],
        "missing": ["What is the minimum model size for CoT to work?"],
        "recommended_experiments": ["Ablation on small models"],
        "confidence_in_answer": "medium",
        "confidence_reason": ""
    }
    monkeypatch.setattr(synth_module, "call_llm", lambda *a, **kw: json.dumps(mock_synth))

    mock_context = {
        "claims": [
            {"text": "CoT improves GSM8K by 40% for 100B+ models.", "arxiv_id": "2201.11903"},
            {"text": "CoT shows no benefit for models under 7B.", "arxiv_id": "2302.00001"},
        ],
        "contradictions": [
            {
                "explanation": "Disagreement on CoT threshold",
                "paper_a": "2201.11903",
                "paper_b": "2302.00001",
                "claim_a": "CoT helps large",
                "claim_b": "CoT doesn't help small"
            }
        ],
        "gaps": [
            {"text": "What is the minimum model size for CoT to work?"}
        ]
    }
    result = synthesize("Does CoT help small models?", mock_context)
    assert "consensus" in result
    assert "disputed" in result
    assert isinstance(result["consensus"], list)
    assert isinstance(result["disputed"], list)