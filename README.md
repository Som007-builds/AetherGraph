# Axion

<p align="center">
  <strong>AI Research Knowledge Graph & Scientific Intelligence Engine</strong>
</p>

<p align="center">
  A multi-agent system for scientific reasoning, contradiction discovery, and research-gap generation across frontier AI literature.
</p>

<p align="center">
  <a href="https://github.com/Som007-builds/AetherGraph"><img src="https://img.shields.io/badge/Version-1.8.0--alpha-blue?style=flat-square" alt="Version"/></a>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js" alt="Next.js"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Neo4j-5.x-008CC1?style=flat-square&logo=neo4j&logoColor=white" alt="Neo4j"/>
  <img src="https://img.shields.io/badge/ChromaDB-0.5-orange?style=flat-square" alt="ChromaDB"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
</p>

---

## Motivation

As the volume of machine learning preprints increases, tracking empirical consistency across papers becomes difficult. Traditional literature search engines are limited to keyword queries and document-level summarization. They cannot query across papers or identify when two studies present conflicting empirical results.

Axion decomposes papers into atomic, falsifiable claims and represents them in a unified knowledge graph. By modeling the relationships between claims, Axion automates contradiction detection, propagates confidence scores based on supporting/contradicting evidence, and flags unexplored research gaps.

---

## System Architecture

Axion parses paper PDFs, extracts structured claims, embeds them for vector search, and stores them in Neo4j to build a semantic claims network.

```
ArXiv PDF ──► Reader Agent ──► Claims ──► Neo4j Graph
                                             │
                                             ▼
                                     Contradiction Agent
                                             │
                                             ▼
                                    Gap Discovery Agent
                                             │
                                             ▼
                                  Coordinator Agent (Query)
                                             │
                                             ▼
                                     Axion UI / API
```

### Technical Stack
* **Vector Store:** ChromaDB for similarity search across claims.
* **Graph Database:** Neo4j 5.x for structural claim relationships.
* **Embeddings:** HuggingFace `sentence-transformers/all-MiniLM-L6-v2`.
* **LLM Orchestration:** Python orchestration layer supporting Groq (Llama 3.1 70B), Gemini 2.0, and Anthropic Claude 3.5.
* **Frontend:** Next.js dashboard with interactive force-directed graph rendering.

---

## Core Capabilities

* **Claim Extraction:** Extracts atomic empirical claims from PDFs with scope, variables, and values.
* **Semantic Claims Graph:** Maps connections between papers, claims, datasets, and methodologies in Neo4j.
* **Contradiction Detection:** Pairs claim embeddings to find semantic overlaps and uses LLM verification to confirm empirical conflicts.
* **Confidence Propagation:** Recalculates confidence scores across the graph based on the ratio of supporting vs. contradicting claim edges.
* **Research Gap Mining:** Scans graph topology to identify isolated nodes, unverified claims, or unexplored combinations of variables.
* **Experiment Design:** Proposes evaluation protocols to resolve detected conflicts.
* **Stateful Query Pipeline:** Orchestrates retrieval, verification, and synthesis to answer research questions with direct citation links.

---

## Example Queries

### Question: Does chain-of-thought prompting benefit small models?

#### 1. Detected Contradiction
* **Source A (Paper 1):** "Chain-of-thought prompting scales reasoning in models >10B parameters, but degrades performance on smaller networks (<5B) due to token drift."
* **Source B (Paper 2):** "By fine-tuning on high-quality step-by-step reasoning tokens, models as small as 1.5B parameters show up to 14% improvement in GSM8k math tasks using chain-of-thought."
* **Conflict Type:** Parameter size threshold limits for CoT utility.

#### 2. Research Gap
* **Gap ID:** `GAP_8829`
* **Description:** Measuring whether instruction tuning alters the parameter threshold at which reasoning degradation occurs in multi-step prompting.

#### 3. Experiment Design Proposal
```json
{
  "protocol_id": "EXP_CONF_981",
  "contradiction_id": "CONTRA_449",
  "objective": "Determine CoT performance thresholds on models between 1B and 8B parameters.",
  "independent_variables": ["Parameter Count (1.5B, 3B, 8B)", "Tuning State (Base vs SFT)"],
  "dataset": "GSM8K",
  "metrics": ["Reasoning Accuracy", "Token Entropy"]
}
```

---

## System Metrics

* **Papers Ingested:** 9
* **Claims Extracted:** 270
* **Contradictions Identified:** 48
* **Research Gaps Identified:** 18
* **Experiment Designs Generated:** 36

---

## Roadmap

* **Structured Claim Ontology:** Move from text descriptions to typed schemas (explicit variables, bounds, and environments).
* **Contradiction Taxonomy:** Classify contradictions by root cause (e.g., data skew, parameter size, prompt format).
* **Ingestion Daemon:** Run automated cron jobs to fetch daily papers from ArXiv RSS feeds matching specific keyword vectors.
* **Citation-Weighted Belief:** Incorporate citation counts and venue metadata into the confidence propagation algorithm.
* **Temporal Scientific Tracking:** Analyze how consensus shifts by tracking claim creation and update dates in the graph.
* **Persistent Agent Memory:** Implement session state for the coordinator agent to retain context across sequential queries.
* **Benchmarking Suite:** Establish evaluation datasets to measure the recall of claim extraction and contradiction detection.

---

## Setup

### Prerequisites
* Python 3.10+
* Node.js 18+ and pnpm
* Docker (for local Neo4j container)
* API Key (Groq, Gemini, or Anthropic)

### 1. Installation
```bash
git clone https://github.com/Som007-builds/AetherGraph.git
cd AetherGraph

# Virtual environment setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python requirements
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the template configuration file:
```bash
cp .env.example .env
```
Update `.env` with your API keys:
```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...
```
Configure your default model provider in config.py:
```python
LLM_PROVIDER = "groq"  # Options: "groq", "gemini", "claude"
```

### 3. Database Deployment
Start local Neo4j:
```bash
docker compose up -d
```
Access the database UI at http://localhost:7474.

### 4. Running the CLI
```bash
# Ingest papers from ArXiv
python main.py --mode ingest --query "chain of thought prompting LLM" --n 5

# Run contradiction detection
python main.py --mode contradict

# Scan for research gaps
python main.py --mode gaps

# Run the query pipeline
python main.py --mode query --query "Does chain-of-thought prompting scale down to models under 3B parameters?"
```

### 5. Running the API and Dashboard
Start the backend server:
```bash
uvicorn api.main:app --port 8000
```

In a new terminal, launch the Next.js frontend:
```bash
cd axion
pnpm install
pnpm dev
```
Open http://localhost:3000 to view the dashboard.

---

## License

This project is licensed under the MIT License. See [LICENSE](file:///d:/AI-Projects/schimesh/LICENSE) for details.
