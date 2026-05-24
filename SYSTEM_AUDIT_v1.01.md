# SciMesh System Audit — Version 1.01

## 1. Executive Summary

Version 1.01 introduces a major upgrade to the coordinator layer and the UI:
- `Coordinator v2` implements a full plan/retrieve/reflect/synthesize agentic loop.
- The UI now supports multi-step coordination, temporal reasoning, and a knowledge graph visualization.
- Temporal analysis has been added via `agents/temporal.py`.

This audit reviews the full codebase, documents new architecture and runtime behavior, and highlights current inconsistencies and risk areas.

---

## 2. New Capabilities in v1.01

### 2.1 Multi-step Coordinator

New modules:
- `agents/planner.py`
- `agents/reflector.py`
- `agents/synthesizer.py`
- `agents/coordinator_v2.py`

Coordinator v2 now follows a four-stage loop:
1. Planner: generate 1–3 focused sub-queries and decide whether to fetch contradictions and gaps.
2. Retriever: query ChromaDB for relevant claims plus contraband/ gaps from SQLite.
3. Reflector: judge if the retrieval context is sufficient, and optionally refine the query.
4. Synthesizer: convert the final context into a structured research report.

A `--v1` CLI flag preserves the legacy single-pass coordinator in `agents/coordinator.py`.

### 2.2 Timeline & Knowledge Graph UI

The Streamlit app now includes:
- a toggle for `Multi-step` coordinator mode
- a `Timeline` tab showing consensus evolution and dispute history
- a `Knowledge Graph` tab rendering a pyvis visualization
- raw JSON and reasoning trace display for v2 outputs

### 2.3 Temporal Reasoning

New `agents/temporal.py` adds:
- year-filtered semantic search (`get_claims_by_year_range`)
- consensus evolution analysis (`get_consensus_evolution`)
- contradiction timeline analysis (`get_contradiction_timeline`)

Temporal context is optionally injected into the final synthesis when the question appears time-aware.

### 2.4 Maintenance Scripts

Two one-off maintenance scripts are present:
- `graph/migrate_add_year.py` to add `paper_year` to the `claims` table
- `graph/backfill_chroma_year.py` to populate Chroma metadata with `paper_year`

---

## 3. Architecture & Data Flow

### 3.1 Ingestion

The ingestion flow remains the same:
- search ArXiv, download PDFs, parse sections
- embed paper chunks in Chroma
- extract falsifiable claims via LLM
- store paper metadata and claims in SQLite
- add claim embeddings to Chroma

### 3.2 Contradiction Detection

Unchanged core flow:
- retrieve all claims from SQLite
- for each claim, retrieve semantically similar claims from Chroma
- classify pairs with LLM
- persist non-`UNRELATED` relationships

### 3.3 Gap Finding

Still uses cluster gap extraction from claim neighborhoods.
The `extract_future_work_gaps()` function exists but remains unused in the standard gap-finding pipeline.

### 3.4 Querying

Two paths now exist:
- `v1` single-pass synthesis: semantic search → contradictions → gaps → one-shot report
- `v2` multi-step agentic loop: planner → retrieve → reflect → synthesize

The Streamlit UI defaults to v2 and exposes the older v1 route as a fallback.

### 3.5 Temporal UI

The UI timeline tab uses:
- `get_consensus_evolution()` to build an evolution narrative and per-year positions
- `get_contradiction_timeline()` to analyse dispute emergence and resolution
- Plotly charts in `ui/timeline.py`

---

## 4. Key Files and Responsibilities

- `main.py`: CLI with `--mode` and `--v1` support
- `config.py`: environment, model, path, and threshold settings
- `llm.py`: provider abstraction with support for Groq, Gemini, and Claude
- `graph/schema.py`: SQLite schema creator
- `graph/queries.py`: DB CRUD and retrieval helpers
- `embeddings/store.py`: ChromaDB persistent client and semantic search wrappers
- `ingestion/arxiv_client.py`: ArXiv search + PDF download
- `ingestion/pdf_parser.py`: PDF text extraction and section chunking
- `agents/reader.py`: LLM claim extraction and storage
- `agents/contradiction.py`: claim relationship detection
- `agents/gap_finder.py`: gap discovery
- `agents/planner.py`: retrieval planning
- `agents/reflector.py`: context sufficiency evaluation
- `agents/synthesizer.py`: final report generation
- `agents/coordinator_v2.py`: orchestrates multi-step reasoning
- `agents/temporal.py`: temporal reasoning and dispute history
- `ui/app.py`: Streamlit UI, query interface, timeline, graph
- `ui/graph_viz.py`: graph export to HTML
- `ui/timeline.py`: plotly chart construction

---

## 5. Outstanding Issues & Risks

### 5.1 Schema / metadata mismatch

The biggest risk in this version is a structural mismatch between database schema and application logic:
- `graph/schema.py` still defines the `claims` table without a `paper_year` column.
- `graph/queries.py` uses `paper_year` in `insert_claim()`, `get_all_claims()`, and `get_claims_in_year_range()`.
- `agents/temporal.py` depends on `paper_year` both in SQLite and in Chroma metadata.

That means a fresh database created with `init_db()` will not support claim insertion or temporal queries unless the migration script is run manually and the claims table is altered.

### 5.2 Claim ingestion does not preserve year data

Even when the migration is applied, `agents/reader.py` does not pass `paper_year` into `insert_claim()`, so newly ingested claims will not have `paper_year` set.
- This also means new Chroma claim metadata lacks `paper_year` for timeline filtering.

### 5.3 Requirements file is incomplete

The Streamlit UI now uses dependencies not listed in `requirements.txt`:
- `pyvis` for graph visualization
- `plotly` for timeline charts

Without these packages, the new UI tabs will fail.

### 5.4 Temporal heuristics are brittle

`agents/coordinator_v2.py` decides whether a question is temporal by checking for keywords in the first 6 words and then truncating the topic to the first 6 words.
- This can misclassify questions and produce poor temporal context injection.

### 5.5 LLM JSON parsing remains fragile

Planner, reflector, and synthesizer all parse raw LLM output as JSON with a simple fallback.
- If the model returns malformed JSON, the system may silently default to fallback behavior.
- Reflector defaults to a sufficient score on parse failure, which can prematurely end retrieval loops.

### 5.6 Legacy gap extraction still unused

`extract_future_work_gaps()` is defined but not integrated into `run_gap_finding()`, so paper-level future-work gap mining is not part of the standard pipeline.

### 5.7 Knowledge graph edge reliability

The graph UI adds contradiction edges for all stored `CONTRADICTS` relationships.
- There is no provenance filter for relationship confidence beyond the user-selected minimum confidence threshold.

---

## 6. Recommendations for v1.01 hardening

### 6.1 Fix schema and claim-year propagation

1. Update `graph/schema.py` to add `paper_year INTEGER` to the `claims` table.
2. Modify `agents/reader.py` to pass `paper_year=int(paper_meta['published'][:4])` into `insert_claim()`.
3. Update `embeddings/store.add_claim()` metadata to include `paper_year`.
4. Consider changing `insert_paper()` to store `published` as a normalized date and use that consistently.

### 6.2 Align requirements with UI features

Add at least:
- `pyvis`
- `plotly`

Optionally add `pandas` if future analytics depend on it.

### 6.3 Improve LLM robustness

- Add strict JSON validation and diagnostics for planner / reflector / synthesizer outputs.
- Log parse failures and raw responses clearly.
- Consider a secondary prompt or schema enforcement layer for JSON output.

### 6.4 Integrate migration paths

- Make `init_db()` aware of schema migrations or
- add a documented startup step for `graph/migrate_add_year.py` and `graph/backfill_chroma_year.py`.

### 6.5 Strengthen temporal analysis

- Use a more reliable topic extraction strategy than first-6-word truncation.
- Add a guard to skip temporal injection if `get_consensus_evolution()` returns insufficient data.

---

## 7. Summary

Version 1.01 is a significant and high-value upgrade:
- it adds a true multi-stage coordinator loop,
- extends the UI with timeline and graph analytics,
- and adds temporal reasoning support.

However, the current codebase has a critical data-model gap around `paper_year`, and the new UI dependencies are not reflected in `requirements.txt`. Fixing those two areas will make the upgraded system stable and deployable.
