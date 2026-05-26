# AXION

### Claims-Native Multi-Agent Scientific Reasoning & Intelligence Engine

---

<p align="center">
  <img src="https://img.shields.io/badge/Version-2.30--beta-blue?style=flat-square" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js" alt="Next.js"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Neo4j-5.x-008CC1?style=flat-square&logo=neo4j&logoColor=white" alt="Neo4j"/>
  <img src="https://img.shields.io/badge/ChromaDB-0.5-orange?style=flat-square" alt="ChromaDB"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
</p>

---

AXION is a multi-agent scientific reasoning platform built with FastAPI, Neo4j, ChromaDB, and Next.js. It extracts atomic, parameter-scoped, falsifiable empirical claims from ArXiv PDF publications, maps them into a property knowledge graph, and automatically audits them for logical contradictions.

```
                  ┌──────────────────────────────┐
                  │      Ingest & Segment        │
                  │  (ArXiv PDFs -> Parser)      │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │    Atomic Claim Extraction   │
                  │  (Structured JSON Prompts)   │
                  └──────────────┬───────────────┘
                                 ▼
        ┌────────────────────────┴────────────────────────┐
        ▼                                                 ▼
┌────────────────────────┐                        ┌───────────────┐
│  Vector Embedding Map  │                        │  Property Map │
│  (ChromaDB Vector Store)│                       │ (Neo4j Graph) │
└────────┬───────────────┘                        └───────┬───────┘
         │                                                │
         └───────────────┬────────────────────────────────┘
                         ▼
        ┌─────────────────────────────────────────────────┐
        │       Multi-Agent Logical Verification          │
        │    (Pruning -> Contradiction Audit -> Gaps)    │
        └────────────────────────┬────────────────────────┘
                                 ▼
        ┌─────────────────────────────────────────────────┐
        │        Confidence & Belief Propagation          │
        │    (Topological update and clamping)            │
        └─────────────────────────────────────────────────┘
```

---

## Project Overview

In domains such as frontier machine learning and quantum computing, the volume of daily preprints and literature scales faster than a researcher can consume. Traditional search engines and standard document-level Retrieval-Augmented Generation (RAG) applications operate over unstructured text blocks and fail to identify underlying empirical conflicts. 

AXION operates at the granularity of **atomic empirical assertions** instead of whole documents. It maps these assertions in a unified property graph to determine scientific consensus, trace timelines of empirical evolution, locate unexplored parameter spaces, and auto-recommend physical experimental designs to resolve literature conflicts.

---

## System Architecture

AXION is structured in a decoupled three-tier architecture:

| Tier | Technologies | Role |
| :--- | :--- | :--- |
| **Frontend (Axion UI)** | Next.js 16, React, TypeScript, Tailwind CSS | Immersive researcher workspace featuring force-directed 2D/3D graphs, contradiction browsers, and a stateful reasoning console tracking multi-step agent actions. |
| **Backend (FastAPI Services)** | Python 3.10+, FastAPI, Uvicorn | Serves REST API endpoints, manages connection pools, runs embedding calculations, and coordinates specialized Python agents. |
| **Database Tier** | Neo4j 5.x Property Graph, ChromaDB Vector Store | Neo4j maps structural nodes and logical relationships. ChromaDB stores semantic vectors of claim texts for candidate matching. |

---

## Core Features

*   **Atomic Claim Extraction:** Parses incoming layout elements and extracts structured claims detailing `subject`, `predicate`, `object`, `conditions`, `metric`, `direction`, and `evidence_span`.
*   **Logical Contradiction Mapping:** Pairs semantic search neighbors with LLM-backed verification to identify true logical conflicts.
*   **Belief Propagation:** Dynamically updates claim confidence metrics across the graph structure when supporting or contradicting evidence changes.
*   **Research Gap Synthesis:** Analyzes topological voids and stated limitations to generate new research hypotheses.
*   **Experiment Recommendations:** Auto-designs structured experimental protocols (dataset, models, metrics, cost) linked directly to the contradictions they aim to resolve.
*   **Plan-Retrieve-Reflect-Synthesize Loop:** The Coordinator v2 Agent generates target queries, validates context density via a reflection loop, and synthesizes cited research reports.

---

## Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+ and pnpm
*   Docker (for running Neo4j container)
*   LLM API Keys (Groq, Gemini, or Anthropic)

### 1. Backend & CLI Installation
Clone the repository and install requirements inside a Python virtual environment:
```bash
git clone https://github.com/Som007-builds/AetherGraph.git
cd AetherGraph

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the project root:
```bash
cp .env.example .env
```
Update `.env` with your API keys and configuration properties:
```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...

NEO4J_URI=bolt://localhost:7887
NEO4J_USER=neo4j
NEO4J_PASSWORD=scimesh123
```

### 3. Run the Databases
Start the Neo4j container:
```bash
docker compose up -d
```
Access the database console at http://localhost:7474.

### 4. Running via CLI
Run tasks directly using the SciMesh CLI:
```bash
# Ingest papers from ArXiv matching a query
python main.py --mode ingest --query "chain of thought prompting LLM" --n 5

# Run contradiction scans on ingested claims
python main.py --mode contradict

# Find research gaps across claim clusters
python main.py --mode gaps

# Run the query pipeline with Coordinator v2
python main.py --mode query --query "Does chain-of-thought prompting scale down to models under 3B parameters?"
```

### 5. Running the API and Workspace UI
Start the FastAPI server:
```bash
uvicorn api.main:app --port 8000
```
In a new terminal, launch the Next.js development server:
```bash
cd axion
pnpm install
pnpm dev
```
Open http://localhost:3000 to interact with the workspace.

---

## Author's Note & Transparency

> **Systems Architecture Assessment**
> 
> I am the Systems Architect of AXION. I designed the graph topology, the multi-agent reasoning loops, and the product vision. To build this at scale, I used AI assistants (Claude, Gemini, ChatGPT) as my syntax engines to heavily accelerate the Python backend and Cypher queries. Because of this, the architecture is state-of-the-art, but the underlying code has technical debt. I am actively learning to fully own the backend, but I am open-sourcing this now because the scientific community needs this tool.

---

## Contributing / Help Wanted

AXION is a state-of-the-art research architecture, but we need community support to harden the codebase and prepare it for production scale. We are actively seeking pull requests for the following core technical debts:

*   **Infrastructure Decoupling:** The FastAPI ingestion loop is currently synchronous and blocks threads. We need help moving PDF parsing to an async worker queue (e.g., Celery/Redis).
*   **Algorithmic Rigor:** The confidence propagation engine currently uses a naive linear heuristic (+0.08/-0.12). We need ML engineers to help transition this to a Bayesian Belief Network or GNN.
*   **Ontology Hardening:** Claims are currently unstructured text. We need help mapping extracted claims to a strict PEFT JSON schema to reduce contradiction false positives.

For contributions, please fork the repository, create a branch, and submit a PR to `Som007-builds/AetherGraph`.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
