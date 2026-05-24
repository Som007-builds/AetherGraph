# SciMesh — Multi-Agent Research Knowledge Graph

A multi-agent system that reads AI/ML papers from ArXiv, builds a persistent 
knowledge graph, detects contradictions between papers, and surfaces research gaps.

## Agents
- **Agent 1: Reader** — Extracts falsifiable claims from papers
- **Agent 2: Contradiction Detector** — Finds semantic contradictions between claims
- **Agent 3: Gap Finder** — Surfaces unanswered research questions
- **Agent 4: Coordinator** — Synthesizes everything for a research question

## Setup
```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API key.

## Usage
```bash
python main.py --mode ingest --query "chain of thought prompting" --n 10
python main.py --mode contradict
python main.py --mode gaps
python main.py --mode query --query "Does CoT help small models?"
python main.py --mode query --query "Does CoT help small models?" --v1
```

## Streamlit UI
Run the dashboard to interact with the multi-step coordinator and timeline views:
```bash
streamlit run ui/app.py
```

The UI supports:
- Multi-step coordinator mode with planner/retriever/reflector/synthesizer loop
- Raw reasoning trace for v2 answers
- Temporal consensus evolution and contradiction timeline charts
- Knowledge graph visualization generated with `pyvis`

## Version 1.10

This repository is currently at **v1.10**, including:
- Neo4j graph migration for paper/claim/gap storage
- Gap linking with `RELATED_TO` relationships
- Planner hardening against malformed LLM sub-query output
- ChromaDB ingestion made idempotent via `upsert()`
- Full audit document in `SYSTEM_AUDIT_v1.10.md`
- Verified `83 passed` on `tests/test_aethergraph.py`

For details, see `SYSTEM_AUDIT_v1.10.md`.
