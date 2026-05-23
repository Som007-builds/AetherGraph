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
```