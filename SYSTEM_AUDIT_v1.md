# SciMesh System Audit — Version 1

## 1. Overview

SciMesh is a research knowledge graph prototype for AI/ML literature. It ingests ArXiv papers, extracts falsifiable claims with an LLM, stores claims in a graph-like SQLite schema, indexes semantic embeddings with ChromaDB, detects claim relationships (contradictions/support), identifies research gaps, and provides a Streamlit UI for synthesis and querying.

This audit documents the architecture, component responsibilities, data flow, runtime paths, and current issues.

---

## 2. Core Architecture

### 2.1 Primary modules

- `main.py`
  - CLI entry point for ingestion, contradiction detection, gap finding, and query synthesis.
  - Initializes SQLite database schema before any action.

- `config.py`
  - Stores environment-driven configuration and constants.
  - Contains API key settings, model selection, directories, and thresholds.

- `llm.py`
  - Provides a single `call_llm()` wrapper.
  - Supports three providers: `groq`, `gemini`, `claude`.
  - Includes basic retry logic for rate limiting.

### 2.2 Data storage

- `graph/schema.py`
  - Creates SQLite tables: `papers`, `claims`, `relationships`, `gaps`.

- `graph/queries.py`
  - CRUD and retrieval functions for papers, claims, relationships, and gaps.
  - Uses `sqlite3` directly, no ORM despite `sqlalchemy` listed in requirements.

### 2.3 Embeddings

- `embeddings/store.py`
  - Initializes a persistent ChromaDB client at `data/db/chroma`.
  - Uses `SentenceTransformerEmbeddingFunction` with model `all-MiniLM-L6-v2`.
  - Provides functions for adding chunks/claims and semantic search.

### 2.4 Ingestion and parsing

- `ingestion/arxiv_client.py`
  - Searches ArXiv via `arxiv` package.
  - Downloads PDF files from `https://arxiv.org/pdf/{arxiv_id}`.

- `ingestion/pdf_parser.py`
  - Extracts full PDF text using PyMuPDF (`fitz`).
  - Splits text into sections by inspecting lines for common headers.
  - Produces overlapping fixed-size chunks for embedding.

### 2.5 Agents

- `agents/reader.py`
  - Extracts papers and claims.
  - Stores metadata in SQLite and embeddings in Chroma.
  - Uses LLM prompts to identify falsifiable claims from key sections.

- `agents/contradiction.py`
  - Locates semantic claim pairs using Chroma search.
  - Evaluates pairs with an LLM to classify them as `CONTRADICTS`, `SUPPORTS`, or `UNRELATED`.
  - Persists non-`UNRELATED` relationships.

- `agents/gap_finder.py`
  - Detects research gaps from clusters of similar claims.
  - Contains an unused function to extract future-work gaps from text.

- `agents/coordinator.py`
  - Synthesizes answers for arbitrary research questions.
  - Uses claim similarity, stored contradictions, and stored gaps.
  - Returns a JSON report with consensus, disputes, missing questions, and recommendations.

### 2.6 UI

- `ui/app.py`
  - Streamlit dashboard delivering:
    - knowledge graph stats
    - query synthesis via coordinator
    - contradiction list
    - research gap list

- `test_claims.py`
  - Debug helper that prints the first 5 stored claims.

---

## 3. Data Flow

### 3.1 Ingestion path (`main.py --mode ingest`)

1. `main.py` calls `init_db()`.
2. ArXiv is searched via `search_papers()`.
3. PDFs are downloaded with `download_pdf()`.
4. Each paper is processed in `process_paper()`:
   - `insert_paper()` stores paper metadata.
   - `extract_sections()` breaks PDF text into named sections.
   - `chunk_text()` creates overlapping chunks and stores them in Chroma using `add_chunk()`.
   - The reader prompts the LLM for claims from key sections and stores each claim in SQLite plus Chroma.

### 3.2 Contradiction detection (`main.py --mode contradict`)

1. `get_all_claims()` loads all claims from SQLite.
2. For each claim, `find_similar_claims()` retrieves semantically related claims.
3. Candidate pairs are filtered by claim identity and same-paper duplicates.
4. The LLM classifies each pair, and any non-`UNRELATED` relationship is inserted.

### 3.3 Gap finding (`main.py --mode gaps`)

1. `run_gap_finding()` executes `find_cluster_gaps()` only.
2. It selects seed claims across the claim set and finds nearby claims.
3. The LLM abstracts a cluster-level research gap and stores it.
4. The “future-work extraction” path in `gap_finder.py` is defined but not used in this flow.

### 3.4 Question answering (`main.py --mode query` / Streamlit)

1. `agents.coordinator.run()` searches claim embeddings for the question.
2. It selects relevant contradictions and gaps.
3. A synthesis prompt is sent to the LLM.
4. Response JSON is parsed and formatted as a report.

---

## 4. Strengths

- Clear separation of responsibilities across modules.
- Persistent graph model for papers, claims, relationships, and gaps.
- Semantic search with local sentence-transformer embeddings.
- Multi-provider LLM abstraction.
- Streamlit UI for interactive query synthesis.
- CLI entry point exists and matches README usage.

---

## 5. Issues and Risks

### 5.1 Data model issues

- `gaps.related_claim_ids` is documented as related claim IDs, but `extract_future_work_gaps()` passes a paper ID, creating schema inconsistency.
- `graph/queries.py` uses JSON strings for authors and related IDs, which works but requires careful decoding everywhere.

### 5.2 Feature surface mismatches

- `gap_finder.py` includes `extract_future_work_gaps()` but `run_gap_finding()` does not call it.
- `main.py` mode `gaps` only finds cluster gaps, so future-work gap extraction is effectively dead code.

### 5.3 Potential contradiction threshold issue

- `agents/contradiction.py` uses `distance > CONTRADICTION_THRESHOLD` to skip candidate claims. Because Chroma distances are similarity-like, this comparison may exclude relevant pairs or include poor matches depending on the embedding distance scale.

### 5.4 LLM parsing fragility

- Several modules attempt to parse raw LLM output as JSON after stripping fences. If the model returns malformed JSON, the system may silently skip claims or relationships.

### 5.5 Missing integration checks

- No validation ensures `data/db/chroma` exists before Chroma usage, though Chroma's client initialization will create it if needed.
- The system assumes required API keys and model packages are available for the selected provider.

---

## 6. Recommended Improvements

### 6.1 Functional fixes

1. Make `gap_finder.run_gap_finding()` combine future-work and cluster gap extraction.
2. Fix `extract_future_work_gaps()` to pass claim IDs or change schema to accept paper IDs.
3. Clarify the contradiction threshold semantics and possibly use cosine similarity explicitly.
4. Add stronger JSON validation in LLM response parsing and fallback logging.

### 6.2 Usability improvements

1. Add structured logging for extraction, contradiction, and gap-finding runs.
2. Implement an explicit CLI or task for `schema.init_db()` beyond startup.
3. Add tests around Graph ingestion and LLM prompt parsing.

### 6.3 Documentation

1. Update `README.md` to specify which LLM provider is supported in practice and how to set `.env`.
2. Document the difference between `claim_id`, `paper_id`, and `related_claim_ids` in the schema.

---

## 7. Audit Summary

This codebase is a coherent version-1 prototype with a working architecture for ingesting papers, storing claims, running semantic search, and using LLMs for reasoning. The main risk areas are schema consistency, unused gap-detection paths, and brittle LLM output parsing. The system is ready for a second iteration focused on robustness, validation, and a more stable query pipeline.
