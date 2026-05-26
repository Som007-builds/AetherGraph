# AXION: Technical State & Systems Maturity Report
**System Version:** v2.30  
**Data Tier:** Neo4j Property Graph (Bolt @ 7887) + ChromaDB Vector Store  
**Engine Class:** Multi-Agent Scientific Reasoning & Claims Intelligence Platform  
**Date of Assessment:** May 26, 2026  

---

## 1. Project Identity

AXION is currently a hybrid property-graph and vector-database claims intelligence repository. The system is engineered to ingest scientific literature, decompose it into atomic empirical assertions (claims), logical structures, and parameters, audit those assertions for contradictions, update belief scores dynamically across the network topology, and recommend experiments to resolve identified disputes.

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
│  (ChromaDB vector lookup)                       │ (Neo4j Graph) │
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

### What AXION Is Not
*   **Not a Chatbot:** AXION does not function as an open-domain conversational agent. It does not generate creative text or answer queries using raw, unverified web-search content.
*   **Not a PDF Summarizer:** It does not produce paragraph-level summaries of individual publications.
*   **Not a Generic RAG App:** It does not run simple top-k chunk retrieval to inject raw context into an LLM generation prompt.

### What AXION Is
AXION is a **Claims-Native Scientific Reasoning Infrastructure**. It decouples linguistic similarity from logical assessment. The system acts as a structured modeling layer over natural language literature, converting unstructured scientific texts into a deterministic, verifiable network of empirical claims, supporting references, contradictions, and open parameters.

---

## 2. Current System Maturity

The following matrix represents the engineering team's current assessment of subsystem maturity, based on runtime correctness, structural reliability, and error handling.

| Subsystem | Maturity Rating | Engineering Justification |
| :--- | :--- | :--- |
| **Ingestion Pipeline** | Production-like | Features isolated section processing, robust PDF text recovery (via PyMuPDF), automatic socket timeouts, and exponential backoff. Individual paper parser failures do not stop batch processes. |
| **Orchestration (Coordinator v2)** | Promising | Orchestrates the Plan-Retrieve-Reflect-Synthesize loop cleanly. The Reflection agent successfully triggers search query refinement loops when context density is low. |
| **Graph Infrastructure (Neo4j)** | Strong | Driver connection pooling, transaction execution, and index/constraint configurations are stable. Graph writes and traversals execute reliably. |
| **Contradiction Engine** | Experimental | Cosine-distance pruning is efficient, but the subsequent LLM logical verification is highly sensitive to prompt configuration and prone to flagging differences in parameter settings as logical conflicts. |
| **Confidence Propagation** | Medium | Updates execution paths across graph updates correctly, but uses a naive, linear heuristic model that ignores source citation weight, venue authority, and chronological decay. |
| **Ontology Quality** | Prototype | Claims are still largely unstructured free-text strings. Optional structured parameter fields are captured but not strictly validated against a scientific ontology schema. |
| **Synthesis Quality** | Medium | Generates detailed cited markdown reports, but suffers from occasional redundancy and shallow integration when retrieving overlapping publications. |
| **Query System** | Promising | Multi-query planner and context density evaluations perform effectively. Loops are terminated reliably when the maximum iteration threshold is reached. |
| **UI/UX** | Medium | Provides a highly responsive dark workspace and force-directed graph canvas, but rendering large graphs causes browser performance degradation. |
| **Observability** | Strong | The `/api/metrics` endpoint provides production-grade tracking of API latencies, provider distribution, and cache rates. `@trace_agent` records execution performance. |
| **Fault Tolerance** | Strong | Centralized parser fallbacks (`safe_json_parse`), section-level try/except blocks, and provider-level fallback chains protect process integrity. |
| **Testing** | Strong | Features 94 fully mocked unit and integration tests executing in under 8 seconds, ensuring offline verification is hermetic. |
| **Scalability** | Weak | Lacks async task queues (e.g., Celery/RabbitMQ) for ingestion, causing synchronous blocking of API threads. Ingest execution is serial. |
| **Scientific Rigor** | Medium | Every synthesized point points directly back to a citation and section in Neo4j, but the system is vulnerable to hallucinated claims during extraction if LLM formatting instructions are violated. |

---

## 3. What Currently Works Well

*   **Orchestration Visibility:** The implementation of the `@trace_agent` decorator and runtime logging allows precise tracking of agent execution states (START, COMPLETE, FAILED) and elapsed time. In the UI, the console log view provides real-time visibility into the agent's reasoning steps.
*   **Operational Resilience:** The rate-limiting fallback chain (`llm.py`) handles API failures effectively. If Groq hits a 429 rate limit, the router waits using exponential backoff with jitter, and falls back to Gemini if retries are exhausted, preventing application crashes.
*   **Graph-Native Reasoning Direction:** Utilizing Neo4j for relationship-driven queries (`CONTRADICTS`, `SUPPORTS`, `RELATED_TO`) outperforms simple vector search. It enables recursive traversal to uncover chains of disagreement and support.
*   **Ingestion Robustness:** Parsing layout sections using PyMuPDF and routing claims through `normalize_claim_output()` ensures that LLM formatting variations (markdown blocks, conversational prefixes) are normalized safely.
*   **Research Gap and Experiment Recommendation:** The system successfully mines literature limitations and clusters vector spaces to construct `:Gap` nodes, generating structured evaluation protocols (JSON schemas) for disputes.

---

## 4. What Is Still Weak

*   **Contradiction Precision (False Positives):** The engine frequently flags claims as contradictions when they are simply complementary. For example, "Method A performs well under condition X" and "Method A degrades under condition Y" are mapped as a conflict because the engine fails to isolate the parameter conditions.
*   **Semantic Mismatch Mappings:** The initial similarity pruning relies on vector distance. Scientific assertions using different terminologies to describe the same mechanism (or vice versa) create semantic drift, producing either irrelevant comparisons or missing edges.
*   **Weak Ontology Validation:** Claims inside the graph do not strictly adhere to a formal schema. The system does not validate whether a claim's `subject`, `predicate`, and `object` conform to a standardized scientific taxonomy.
*   **Linear Confidence Model:** The belief-updating formula:
    $$\text{Confidence} = \text{BaseConfidence} + (0.08 \times N_{\text{supports}}) - (0.12 \times N_{\text{contradictions}})$$
    is mathematically naive. It treats all supporting and contradicting claims as having equal weight, exposing the graph to manipulation by single papers containing multiple redundant claims.
*   **Shallow Synthesis:** The coordinator's final report generation sometimes lists retrieved claims sequentially rather than integrating them into a coherent argument. It can struggle with information redundancy when multiple papers cite the same primary source.
*   **Temporal Reasoning Limitations:** Mapping chronological consensus is limited to grouping papers by year. The system does not understand the lineage of ideas, version changes in models, or the historical decay of older scientific paradigms.

---

## 5. The Hardest Unsolved Problems

### 1. Structured Scientific Representation
Translating natural language research papers into a mathematically rigorous knowledge representation (e.g., structured ontology of variables, units, bounds, and directional functions) without losing experimental nuance is an open problem. If variables are too broad, contradictions are false; if too narrow, the graph remains isolated.

### 2. High-Precision Contradiction Filtering
Detecting true empirical contradictions requires the system to align the entire experimental setup (parameter configurations, datasets, evaluations). LLMs struggle to maintain this context across multiple long-form descriptions, leading to high false-positive rates on complex comparisons.

### 3. Topological Scientific Uncertainty Propagation
Uncertainty in science is non-linear. Presenting belief propagation across an arbitrary graph network where nodes represent claims with varying degrees of certainty, and edges represent logical relationships, requires a formal probabilistic graphical model (e.g., Bayesian Belief Networks) rather than linear heuristics.

---

## 6. Current Architectural Direction

AXION is evolving from a document-level retrieval architecture to a **graph-native scientific reasoning infrastructure**.

```
Document Retrieval (RAG)                  Claims-Native Reasoning
┌───────────────────────────┐             ┌───────────────────────────┐
│     Natural Language      │             │     Natural Language      │
│          Query            │             │          Query            │
└────────────┬──────────────┘             └────────────┬──────────────┘
             ▼                                         ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   Top-K Text Retrieval    │             │   Deconstruction & Plan   │
└────────────┬──────────────┘             └────────────┬──────────────┘
             ▼                                         ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│    LLM Summary Report     │             │  Claims Extraction Map    │
└───────────────────────────┘             └────────────┬──────────────┘
                                                       ▼
                                          ┌───────────────────────────┐
                                          │   Logical Verification    │
                                          └────────────┬──────────────┘
                                                       ▼
                                          ┌───────────────────────────┐
                                          │  Topological Propagation  │
                                          └────────────┬──────────────┘
                                                       ▼
                                          ┌───────────────────────────┐
                                          │  Provenance Cited Report  │
                                          └───────────────────────────┘
```

This evolution requires addressing several architectural considerations:
*   **Decoupled Async Ingestion:** Ingestion must move out of the FastAPI request-response thread into background task queues (e.g., Celery/RabbitMQ). Large PDF parsing and vector generation are too heavy for synchronous loops.
*   **Strict Ontology Schemas:** Future databases must replace free-text properties with strict node types representing variables, datasets, and benchmarks.
*   **Hermetic Agent Interfaces:** Agents must be governed by strict data contracts, allowing hot-swapping of prompt templates and underlying LLM models without affecting graph write operations.
*   **Absolute Provenance Grounding:** The system must transition to storing pixel-level coordinates and paragraph bounding boxes for every claim extraction, enabling researchers to verify claims directly inside the UI.

---

## 7. Current Graph System Analysis

```
              ┌───────────────┐
              │    Paper      │
              │  - arxiv_id   │
              │  - title      │
              └───────▲───────┘
                      │
                      │ EXTRACTED_FROM
                      │
┌──────────────┐      │       ┌──────────────┐
│    Claim     ├──────┼──────►│    Claim     │
│ (Claim A ID) │◄─────┴──────┤ (Claim B ID) │
└──────┬───────┘ CONTRADICTS  └──────┬───────┘
       │                             │
       └──────────────┬──────────────┘
                      │ RELATED_TO
                      ▼
              ┌───────────────┐
              │     Gap       │
              │  - gap_id     │
              │  - text       │
              └───────────────┘
```

*   **Node Integrity:** 
    *   `:Paper` nodes successfully record metadata (arxiv ID, title, authors, year).
    *   `:Claim` nodes capture extracted text and confidence scores.
    *   `:Gap` nodes are generated from clusters of claims and limitations.
*   **Edge Density:**
    *   `EXTRACTED_FROM` edges are highly reliable.
    *   `CONTRADICTS` and `SUPPORTS` edges are sparse, representing isolated claims. The graph is currently a collection of star topologies centered around individual papers, with relatively few cross-paper connections.
*   **Clustering:** Vector similarity clustering successfully clusters claims inside vector space, but these clusters do not translate into first-class graph entities inside Neo4j. The database does not run graph clustering algorithms (e.g., Louvain or Leiden) natively.
*   **Limits of the Graph:** The graph cannot represent logical hierarchy. It does not know if one claim is a subset of another, nor does it capture the experimental variables as discrete nodes.

---

## 8. Contradiction Engine Analysis

The contradiction agent currently uses the following prompt structure to evaluate claims:
```
Compare Claim A and Claim B. 
Determine if they CONTRADICT, SUPPORT, or are UNRELATED.
Verify experimental details, datasets, and conditions.
```

### Key Failure Points
1.  **Scale Mismatch:** Claim A: "LoRA scales parameter efficiency for 7B models." Claim B: "LoRA degrades on models under 1B parameters." The engine flags this as a contradiction, ignoring the parameter constraints (7B vs. 1B).
2.  **Dataset Dependency:** Assertions that report opposite performance on different datasets are flagged as contradictions, ignoring that both assertions can be true.
3.  **Ambiguous Terminology:** "Reasoning performance" and "mathematical capability" are treated as equivalent, leading to false comparisons.

### Future Contradiction Taxonomy
To move beyond simple binary assertions, contradictions must be classified using a structured taxonomy:
*   `METRIC_OPPOSITION`: Directly conflicting measurements under identical conditions.
*   `METHODOLOGY_CLASH`: Disagreement over the validity of an experimental setup.
*   `PARAMETER_DEVIATION`: Conflict arising from scale differences (e.g., context length, model size).
*   `DATASET_DIVERGENCE`: Conflicting findings caused by data distribution shifts.

---

## 9. Confidence System Analysis

The current confidence system updates claims using a basic topological update loop:
```python
new_confidence = base_confidence + (0.08 * N_supports) - (0.12 * N_contradictions)
new_confidence = max(0.05, min(0.98, new_confidence))
```

### NAIVE HEURISTIC LIMITATIONS
*   **No Source Reputation:** A paper with 5,000 citations is weighted the same as a non-peer-reviewed preprint.
*   **Vulnerability to Spams:** A paper repeating a claim multiple times in different sections can artificially boost or penalize a claim's confidence score.
*   **No Propagation Decay:** Edges propagate confidence equally regardless of the distance from the source dispute. A local dispute degrades confidence across the entire semantic neighborhood without attenuation.

---

## 10. Scientific Rigor Analysis

Can AXION be trusted as a scientific tool right now?

> [!WARNING]
> AXION should only be used as a discovery and hypothesis-generation tool. It cannot be used as an autonomous source of scientific truth.

### Key Risks
*   **Hallucination Propagation:** If the extraction step generates a false claim, this claim will propagate through vector space, match other claims, degrade their confidence, and produce erroneous contradiction maps.
*   **Lack of Negative Results:** Scientific literature is biased toward positive results. The graph inherits this bias, leading to over-representing consensus.
*   **No Verification of Bounding Boxes:** The front-end cannot display the exact PDF page or paragraph bounding box of an extracted claim, meaning researchers must search the original PDF manually to verify assertions.

---

## 11. UI/UX Maturity Analysis

### Strengths
*   **Observability Pane:** The agent execution console logs steps clearly.
*   **Force-Directed Graph:** Provides real-time rendering of paper-claim networks.
*   **Workspace Decoupling:** Side rails allow navigation across Graph, Contradictions, and Gaps.

### Weaknesses
*   **Scale Limits:** The React D3 force-directed canvas experiences rendering performance degradation when displaying more than 150 nodes.
*   **Lack of Node Filtering:** The canvas does not support filtering nodes by confidence score, publication year, or extraction source.
*   **No Contextual Zoom:** Clicking a node does not show the parent PDF context in a split-screen view.

---

## 12. Infrastructure & Scalability Analysis

```
FastAPI Server (Sync Worker Thread)
       │
       ▼
[Reader Agent] ──► [PDF Extraction] ──► [LLM Calls (Groq/Gemini)]
       │
       ▼
   (Blocked)
```

*   **Synchronous Blockage:** The ingestion execution path is synchronous. If a user requests ingestion for $N=15$ papers, the request-response cycle is blocked, tying up the thread.
*   **No Task Queue:** Without a distributed task queue (like Celery/RQ with Redis), the backend cannot queue concurrent ingestion requests.
*   **Rate Limits:** Although LLM routing has fallbacks, synchronous retry sleeps (`time.sleep`) stall execution threads.
*   **ChromaDB Limitations:** ChromaDB runs as a local persistent client. It cannot scale horizontally and blocks parallel writes.

---

## 13. Testing & Reliability Analysis

*   **Unit Tests (94/94 Green):** The unit test suite in `tests/` covers config parsers, citation formulas, agent output normalization, and regression tests. Mocks ensure that tests run in under 8 seconds without requiring live API keys.
*   **Smoke Test (43/43 Green):** `test_phase5.py` validates database connection layers, Neo4j schema indices, and ChromaDB type constraints.
*   **Testing Gaps:**
    *   No concurrency tests verifying SQLite or Neo4j transaction states under simultaneous write loads.
    *   No validation checks for HuggingFace model weight caching. If HuggingFace Hub is down, the embedding pipeline crashes silently.

---

## 14. Product Positioning Analysis

| Tool | Core Capability | AXION Difference |
| :--- | :--- | :--- |
| **Generic RAG** | Document summarizing | AXION extracts, maps, and reasons over atomic claims. |
| **Perplexity** | Natural language answers | Perplexity provides search summaries; AXION builds a persistent, evolving graph of claims. |
| **Google Scholar** | Document search | Scholar indexes documents; AXION maps logical contradictions and consensus. |
| **Graph Databases** | Data relation modeling | Neo4j stores generic links; AXION automates claim extraction, relationship mapping, and confidence propagation. |

AXION is converging toward a **Claims-Native Scientific Reasoning Infrastructure**. It is designed to act as an operating system for literature analysis, enabling researchers to run virtual evaluations over scientific assertions.

---

## 15. Strategic Priorities

### 1. Structured Scientific Ontology (PEFT Ontology)
Move from free-text strings to structured claims with typed nodes for variables, datasets, and metrics.
*   *Why:* Eliminates semantic drift and enables deterministic logical auditing.

### 2. Parameter-Aware Contradiction Checks
Improve contradiction verification by comparing variables, model configurations, and thresholds.
*   *Why:* Reduces contradiction false positives.

### 3. Pixel-Level Provenance Grounding
Store absolute coordinate bounding boxes (page number, paragraph, layout region) for all claims.
*   *Why:* Enables researchers to verify claims directly inside the workspace UI.

### 4. Evidence-Weighted Confidence Propagation
Incorporate citation count, venue impact metrics, and chronological decay into confidence calculations.
*   *Why:* Prevents isolated preprints from distorting established consensus.

### 5. Hierarchical Graph Clustering
Implement graph community detection algorithms (e.g., Louvain/Leiden) in Neo4j.
*   *Why:* Identifies conceptual boundaries and research gaps across domains.

---

## 16. What Should Not Be Built Yet

*   **Multi-User Infrastructure:** Adding authentication and workspace sharing is premature while reasoning precision is still calibrating.
*   **Mobile Workspace Application:** AXION is designed for desktop environments with dense research interfaces and 3D graph canvases.
*   **Heavy Animations:** Polishing visual transitions takes resources away from improving logical verification accuracy.
*   **Autonomous Research Agents:** Deploying autonomous web-scraping research loops without strict validation rules will pollute the graph with low-quality preprints and hallucinated nodes.

---

## 17. Long-Term Vision

```
Continuous Preprints Stream (ArXiv/bioRxiv)
               │
               ▼
   [Ingestion & Claim Deconstruct]
               │
               ▼
    [Property Graph Network] ◄───► [Contradiction Scanning]
               │
               ▼
     [Bayesian Propagation] ──► [Confidence Mapping]
               │
               ▼
  [Autonomous Experiment Design] ──► [Lab Automation / Execution]
```

AXION aims to become an autonomous reasoning layer for scientific literature. The system will continuously monitor academic feeds, update consensus, identify logical contradictions, and design resolving experiments.

---

## 18. Final Engineering Assessment

*   **Overall Project Maturity:** Promising prototype transitioning to stable infrastructure. The backend architecture is robust, but the contradiction and confidence subsystems require calibration.
*   **Strongest Subsystem:** Ingestion & Fault-Tolerant Parsing. The pipeline handles layout parsing and malformed JSON errors gracefully.
*   **Weakest Subsystem:** Contradiction engine precision. The logical validation step is prone to false positives.
*   **Biggest Technical Risk:** Hallucination cascade. Extracted errors propagate through the graph, corrupting downstream confidence scores and gap generation.
*   **Biggest Strategic Opportunity:** Claims-native reasoning database. Building a structured claims repository positions AXION as an alternative to simple text search engines.
*   **Immediate Next Architectural Step:** Define a strict PEFT schema to transition claims from unstructured strings to variable-bounded logical nodes.
