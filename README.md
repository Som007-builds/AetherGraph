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

## 🏢 Why Axion Exists

Scientific literature in artificial intelligence is expanding at a rate that exceeds human bandwidth. Thousands of preprints are uploaded weekly, making it virtually impossible for researchers to:
1. **Identify direct contradictions** in empirical results across different evaluation setups.
2. **Deconstruct papers** into atomic, falsifiable claims rather than narrative summaries.
3. **Track consensus changes** over time as models and benchmarks evolve.

Existing academic search engines and PDF reader systems are built for *document summarization* or *shallow keyword retrieval (RAG)*. They operate on single documents or simple similarity metrics. 

**Axion** shifts the paradigm from search to reasoning. By extracting atomic scientific claims into a structured Neo4j knowledge graph and leveraging a network of specialized agents, Axion dynamically identifies contradictions, updates claim confidence scores, proposes research gaps, and designs resolving experiments.

---

## 🖼️ Interface & Architecture Preview

### Knowledge Graph Visualization
```
[ Placeholder: Knowledge Graph UI ]
docs/images/knowledge_graph.png
```
*Figure 1: Force-directed knowledge graph displaying Papers (blue), atomic Claims (color-coded by confidence), Research Gaps (violet), and their associated relationships (`EXTRACTED_FROM`, `CONTRADICTS`).*

### Contradiction Detection & Resolving Protocols
```
[ Placeholder: Contradiction Reports ]
docs/images/contradiction_reports.png
```
*Figure 2: Empirical contradiction interface highlighting conflicting findings between papers alongside AI-synthesized experiment designs.*

### Scientific Ingestion & Discovery Dashboard
```
[ Placeholder: Research Gaps & Coordinator Synthesis ]
docs/images/gaps_and_synthesis.png
```
*Figure 3: Multi-agent coordination tab tracking the query loop (Plan -> Retrieve -> Reflect -> Synthesize) and listing open research gaps.*

---

## ⚡ Core Capabilities

- **Atomic Claim Extraction:** Extracts falsifiable empirical claims from paper PDFs (via ArXiv), mapping variables, values, and contextual scopes.
- **Neo4j Semantic Network:** Constructs a directional graph connecting papers, claims, datasets, and author entities.
- **Deep Contradiction Discovery:** Employs embedding-based similarity filters combined with LLM cross-examination to flag conflicting scientific assertions.
- **Dynamic Belief Propagation:** Automatically propagates confidence scores through the claim network based on supporting or contradicting evidence.
- **Autonomous Research Gap Mining:** Scans the knowledge graph topology to isolate unverified claims, unexamined variables, and unexplored intersections.
- **Frontier Experiment Recommendation:** Proposes concrete methodologies, datasets, and verification steps to empirical contradictions.
- **Multi-Agent Orchestrator (Coordinator v2):** A stateful agent network that plans, retrieves, reflects, and synthesizes research reports with exact citation mappings.

---

## 📐 System Architecture

The core pipeline processes raw scientific text into a structured, queryable knowledge graph, exposing it through Next.js and Streamlit analytics interfaces:

```
                      ┌────────────────────────┐
                      │    ArXiv Paper feed    │
                      └───────────┬────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │      Reader Agent      │
                      └───────────┬────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │    Falsifiable Claims  │
                      └───────────┬────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │   Neo4j Knowledge Graph│
                      └───────────┬────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Contradiction   │    │  Gap Discovery   │    │    Confidence    │
│      Agent       │    │      Agent       │    │  Updater Agent   │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │  Coordinator Agent /   │
                      │    Query Processor     │
                      └───────────┬────────────┘
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
            ┌──────────────────┐      ┌──────────────────┐
            │    Next.js UI    │      │   Streamlit UI   │
            │     (Axion)      │      │ (Ingestion / CLI)│
            └──────────────────┘      └──────────────────┘
```

### Technical Stack
* **Vector Database:** ChromaDB for similarity indexing of atomic claims.
* **Graph Database:** Neo4j 5.x for structural claim relationships.
* **Embeddings:** HuggingFace `sentence-transformers/all-MiniLM-L6-v2` for lightweight, high-performance semantic retrieval.
* **Agent Foundations:** Groq (Llama 3.1 70B), Google Gemini 2.0 Flash, and Anthropic Claude 3.5 Sonnet.
* **Orchestration:** Python-based multi-agent execution loop with asynchronous task management.

---

## 🔬 Scientific Logic & Output Examples

### Case Study: *Does chain-of-thought prompting benefit small models?*

#### 1. Extracted Contradiction Report
* **Paper A:** *“Chain-of-thought prompting scales reasoning in models >10B parameters, but degrades performance on smaller networks (<5B) due to token drift.”*
* **Paper B:** *“By fine-tuning on high-quality step-by-step reasoning tokens, models as small as 1.5B parameters show up to 14% improvement in GSM8k math tasks using chain-of-thought.”*
* **Analysis:** Semantic contradiction detected on variable `Model Size Bounds` for `CoT Benefits`.

#### 2. Generated Research Gap
* **Gap ID:** `GAP_8829`
* **Topic:** Parameter threshold limits for zero-shot CoT vs. instruction-tuned CoT in math domains.
* **Context:** Graph identifies a lack of claim nodes addressing whether instruction tuning changes the scaling threshold at which token drift degrades reasoning.

#### 3. Recommended Experiment Protocol
```json
{
  "protocol_id": "EXP_CONF_981",
  "contradiction_id": "CONTRA_449",
  "objective": "Establish the performance boundary of zero-shot vs fine-tuned CoT on models between 1B and 8B parameters",
  "independent_variables": ["Parameter Count (1.5B, 3B, 8B)", "Tuning State (Base vs SFT)", "Prompt Length"],
  "dataset": "MATH & GSM8K",
  "metrics": ["Token Entropy", "Final Reasoning Accuracy"]
}
```

---

## 📊 Live System Metrics

* **Active Papers Ingested:** 9
* **Atomic Claims Isolated:** 270
* **System Contradictions Flagged:** 48
* **Verified Research Gaps:** 18
* **Simulated Experiments Proposed:** 36
* **Confidence Recalculation Frequency:** Real-time on graph updates

---

## 🛣️ Project Roadmap

- [ ] **Structured Claim Ontology:** Formalize extraction into a strictly typed schema (Variables, Scopes, Bounds, Modalities) instead of text descriptions.
- [ ] **Contradiction Taxonomy:** Categorize disputes automatically (e.g., *Methodological difference*, *Evaluation metric shift*, *Data distribution skew*).
- [ ] **Autonomous Ingestion Daemon:** Continuous ingestion runner reading daily ArXiv RSS feeds matching configured keyword vectors.
- [ ] **Citation-Weighted Reasoning:** Scale the confidence scores of claims according to their citation counts and publication index.
- [ ] **Temporal Scientific Tracking:** Trace paradigm shifts and belief changes in the database as new papers challenge older research.
- [ ] **Stateful Agent Memory:** Implement persistent cross-session memory for the coordinator to reference previous literature syntheses.
- [ ] **Benchmark Evaluation:** Create an automated evaluation suite to benchmark the extraction accuracy of claims and contradictions.

---

## ⚙️ Setup & Verification

### Prerequisites
* **Python:** 3.10+
* **Node.js:** 18+ and `pnpm`
* **Docker:** Installed and running (for Neo4j)
* **API Keys:** Groq, Gemini, or Anthropic Claude

### 1. Repository Setup & Dependencies
```bash
git clone https://github.com/Som007-builds/AetherGraph.git
cd AetherGraph

# Initialize Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configuration
Copy the environment variables template and configure your keys:
```bash
cp .env.example .env
```
Update `.env` with your API keys:
```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...
```
Configure your default model provider in [config.py](file:///d:/AI-Projects/schimesh/config.py):
```python
LLM_PROVIDER = "groq" # Or "gemini", "claude"
```

### 3. Deploy Neo4j
```bash
docker compose up -d
```
Verify the Neo4j console is accessible at http://localhost:7474.

### 4. CLI Execution (Ingestion & Agent Pipelines)
```bash
# Ingest 5 research papers about chain-of-thought prompting
python main.py --mode ingest --query "chain of thought prompting LLM" --n 5

# Detect contradictions across the ingested claims
python main.py --mode contradict

# Mine the graph for open research gaps
python main.py --mode gaps

# Run the Coordinator Agent query loop
python main.py --mode query --query "Does chain-of-thought prompting scale down to models under 3B parameters?"
```

### 5. Running the API & Next.js Dashboard
Start the FastAPI backend server:
```bash
uvicorn api.main:app --port 8000
```

In a separate terminal, launch the Next.js frontend:
```bash
cd axion
pnpm install
pnpm dev
```
Open http://localhost:3000 to interact with the Axion Scientific Intelligence Dashboard.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](file:///d:/AI-Projects/schimesh/LICENSE) for details.
