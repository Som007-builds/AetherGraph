<p align="center">
  <h1 align="center">AetherGraph</h1>
  <p align="center">
    <strong>Multi-Agent AI Research Knowledge Graph</strong><br/>
    Automated paper ingestion · Contradiction detection · Research gap analysis · Interactive visualization
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Neo4j-5.x-008CC1?logo=neo4j&logoColor=white" alt="Neo4j"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</p>

---

## What is AetherGraph?

AetherGraph is a **multi-agent system** that reads AI/ML research papers from ArXiv, extracts falsifiable claims, builds a persistent knowledge graph, detects contradictions between papers, surfaces research gaps, and synthesizes structured research reports — all powered by LLMs.

**Key capabilities:**
- 🔬 **Automated Paper Ingestion** — Fetches papers from ArXiv, extracts claims with citation weighting
- ⚡ **Contradiction Detection** — Finds semantic contradictions between claims across papers
- 🧩 **Research Gap Analysis** — Identifies unanswered questions from the knowledge graph
- 🧪 **Experiment Design** — AI-generated experiment proposals to resolve contradictions
- 📊 **Dynamic Confidence Scoring** — Claim confidence recalculated based on support/contradiction evidence
- 🕐 **Temporal Analysis** — Tracks how scientific consensus evolves over time
- 🌐 **Interactive Knowledge Graph** — Force-directed visualization of papers, claims, and relationships
- 🤖 **Multi-Agent Coordinator** — Ask natural language questions, get synthesized research reports with citations

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Axion — Next.js Frontend (port 3000)       │
│     Dashboard · Query Panel · Graph Visualization       │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/JSON
                         ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8000)                 │
│                    api/main.py                          │
├──────────────┬──────────────────────┬───────────────────┤
│   Agents     │   Graph Layer        │   Ingestion       │
│  ─────────   │   ───────────        │   ──────────      │
│  Coordinator │   Neo4j Client       │   ArXiv Client    │
│  Reader      │   Queries            │   PDF Parser      │
│  Synthesizer │   Schema             │   Scheduler       │
│  Reflector   │                      │                   │
│  Planner     ├──────────────────────┤                   │
│  Contradiction│  Embeddings         │                   │
│  Gap Finder  │  ───────────         │                   │
│  Temporal    │  ChromaDB Store      │                   │
│  Confidence  │                      │                   │
│  Experiment  │                      │                   │
└──────────────┴──────────────────────┴───────────────────┘
                    │                        │
                    ▼                        ▼
        ┌───────────────────┐    ┌───────────────────┐
        │  Neo4j Graph DB   │    │  ChromaDB Vector   │
        │  Papers · Claims  │    │  Claim Embeddings  │
        │  Gaps · Relations │    │  Similarity Search │
        └───────────────────┘    └───────────────────┘
```

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **pnpm**
- **Docker** (for Neo4j) or a running Neo4j 5.x instance
- An API key for at least one LLM provider: **Groq** (free), **Gemini**, or **Claude**

### 1. Clone and Setup

```bash
git clone https://github.com/Som007-builds/AetherGraph.git
cd AetherGraph

# Python environment
python -m venv venv
# Windows:
venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Choose your LLM provider (set at least one key)
GROQ_API_KEY=your_groq_key          # Free at console.groq.com
GEMINI_API_KEY=your_gemini_key      # Free at aistudio.google.com
ANTHROPIC_API_KEY=your_claude_key   # console.anthropic.com

# Neo4j (defaults work with docker-compose)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=scimesh123
```

Then set your preferred provider in `config.py`:

```python
LLM_PROVIDER = "groq"  # Options: "groq", "gemini", "claude"
```

### 3. Start Neo4j

```bash
docker compose up -d
```

This starts Neo4j on port 7687 with the browser UI at http://localhost:7474.

### 4. Ingest Papers

```bash
# Ingest 5 papers about chain-of-thought prompting
python main.py --mode ingest --query "chain of thought prompting LLM" --n 5

# Detect contradictions
python main.py --mode contradict

# Find research gaps
python main.py --mode gaps
```

### 5. Start the Application

**Terminal 1 — Backend:**
```bash
# Windows:
.\venv\Scripts\uvicorn.exe api.main:app --port 8000
# Linux/macOS:
uvicorn api.main:app --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd axion
pnpm install
pnpm dev
```

Open **http://localhost:3000** — you're ready to go!

---

## Agents

| Agent | Purpose |
|:------|:--------|
| **Reader** | Extracts falsifiable claims from papers using LLM |
| **Contradiction Detector** | Finds semantic contradictions between claims using embeddings + LLM |
| **Gap Finder** | Identifies research gaps from the knowledge graph |
| **Planner** | Decomposes complex questions into sub-queries |
| **Reflector** | Evaluates if enough evidence has been gathered or if more retrieval is needed |
| **Synthesizer** | Produces structured research reports with citations |
| **Coordinator v2** | Orchestrates the multi-agent loop: Plan → Retrieve → Reflect → Synthesize |
| **Temporal** | Tracks how consensus and contradictions evolve over years |
| **Confidence Updater** | Dynamically recalculates claim confidence based on evidence |
| **Experiment Recommender** | Designs experiments to resolve specific contradictions |
| **Citation** | Enriches papers with citation counts from Semantic Scholar |

---

## Frontend Tabs

| Tab | Description |
|:----|:------------|
| **Ask a Question** | Natural language research queries → structured reports with consensus, disputes, gaps, and experiments |
| **Contradictions** | Browse all detected contradictions with expandable experiment designs |
| **Research Gaps** | View identified gaps with linked claims |
| **Timeline** | Temporal consensus evolution and dispute chronology for any topic |
| **Graph Evolution** | Confidence distribution analytics + most-changed claims |
| **Knowledge Graph** | Interactive force-directed visualization of the entire graph |

---

## API Endpoints

All endpoints are under `http://localhost:8000`:

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/api/stats` | Graph statistics (papers, claims, contradictions, gaps) |
| `GET` | `/api/claims` | List all claims with pagination |
| `GET` | `/api/contradictions` | List contradictions with confidence filter |
| `GET` | `/api/experiments/{id}` | Get experiment design for a contradiction |
| `POST` | `/api/experiments/{id}/design` | Generate a new experiment design |
| `GET` | `/api/gaps` | List research gaps |
| `POST` | `/api/query` | Ask a research question (runs the full coordinator pipeline) |
| `GET` | `/api/temporal/evolution` | Consensus evolution for a topic over years |
| `GET` | `/api/temporal/disputes` | Contradiction timeline for a topic |
| `GET` | `/api/confidence/distribution` | Confidence score distribution |
| `GET` | `/api/confidence/most-changed` | Claims with the largest confidence changes |
| `POST` | `/api/confidence/recalculate` | Trigger confidence recalculation |
| `GET` | `/api/ingestion/status` | Last ingestion run info |
| `POST` | `/api/ingestion/trigger` | Trigger a background ingestion cycle |
| `GET` | `/api/graph` | Full graph data (nodes + edges) for visualization |
| `GET` | `/api/health` | Health check |

---

## CLI Reference

```bash
# Ingest papers from ArXiv
python main.py --mode ingest --query "<search query>" --n <count>

# Run contradiction detection
python main.py --mode contradict

# Find research gaps
python main.py --mode gaps

# Ask a question (Coordinator v2 — multi-round)
python main.py --mode query --query "Your research question here"

# Ask a question (v1 — single-round, faster)
python main.py --mode query --query "Your question" --v1
```

---

## Project Structure

```
AetherGraph/
├── agents/                  # All AI agents
│   ├── coordinator_v2.py    # Multi-agent orchestrator
│   ├── reader.py            # Paper → claims extraction
│   ├── contradiction.py     # Contradiction detection
│   ├── gap_finder.py        # Research gap identification
│   ├── synthesizer.py       # Report generation
│   ├── planner.py           # Query decomposition
│   ├── reflector.py         # Evidence sufficiency evaluation
│   ├── temporal.py          # Temporal analysis
│   ├── confidence_updater.py# Dynamic confidence scoring
│   ├── experiment_recommender.py # Experiment design
│   └── citation.py          # Citation enrichment
├── api/                     # FastAPI REST backend
│   ├── main.py              # All endpoints
│   └── models.py            # Pydantic response models
├── axion/                   # Next.js frontend
│   ├── app/                 # Pages and layouts
│   ├── components/axion/    # Feature components
│   ├── components/ui/       # UI primitives (shadcn)
│   ├── lib/api-client.ts    # API client
│   └── types/axion.ts       # TypeScript types
├── graph/                   # Neo4j integration
│   ├── neo4j_client.py      # Driver wrapper
│   ├── neo4j_queries.py     # All Cypher queries
│   └── neo4j_schema.py      # Schema constraints
├── embeddings/              # ChromaDB vector store
├── ingestion/               # ArXiv + PDF pipeline
│   ├── arxiv_client.py      # ArXiv API client
│   ├── pdf_parser.py        # PDF text extraction
│   └── scheduler.py         # Auto-ingestion scheduler
├── config.py                # All configuration
├── llm.py                   # LLM provider abstraction
├── main.py                  # CLI entry point
├── docker-compose.yml       # Neo4j container
├── requirements.txt         # Python dependencies
└── .env.example             # Environment template
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, shadcn/ui, react-force-graph-2d |
| Backend | FastAPI, Uvicorn, APScheduler |
| Graph DB | Neo4j 5.x |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Groq (Llama 3.1) / Gemini 2.0 Flash / Claude Sonnet 4 |
| PDF Parsing | PyMuPDF |

---

## License

MIT
