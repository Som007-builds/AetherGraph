# SYSTEM AUDIT v1.10 — Full System Audit with Live Test Results
**Date:** May 25, 2026
**Version:** 1.10
**Status:** ✅ Audit complete with live test verification

---

## 1. Executive Summary

This audit captures the current state of the SciMesh system after the Phase 4 / v1.10 work, including architecture, migration status, bug fixes, and live test results.

- **Neo4j migration:** complete and functional
- **Gap linking:** implemented with `RELATED_TO` edges
- **Planner hardening:** robust against malformed LLM sub-query outputs
- **Test validation:** `83 passed` on `tests/test_aethergraph.py`
- **Known caution:** legacy SQLite coordinator v1 remains in codebase and should be removed in Phase 5

---

## 2. Audit Scope

This audit covers:
- graph persistence and query layer
- embeddings storage and ingestion
- agent behavior for reader, contradiction, gap finding, and coordinator
- LLM provider abstraction and response parsing
- current test suite status and regression checks

---

## 3. Architecture & Implementation

### 3.1 Current system layers

- **Graph backend:** Neo4j via `graph/neo4j_client.py`, `graph/neo4j_schema.py`, and `graph/neo4j_queries.py`
- **Embedding store:** ChromaDB via `embeddings/store.py`
- **LLM layer:** `llm.py` supports `groq`, `gemini`, and `claude`
- **Agent orchestration:** `agents/coordinator_v2.py` for production coordination; legacy `agents/coordinator.py` remains deprecated
- **UI:** `ui/app.py` provides Streamlit dashboard functionality

### 3.2 Key file responsibilities

- `graph/neo4j_client.py`
  - Neo4j connection management
  - `run_query()` and `run_write()` abstraction

- `graph/neo4j_schema.py`
  - creates constraints and indexes for `Paper`, `Claim`, and `Gap`

- `graph/neo4j_queries.py`
  - manages papers, claims, contradictions, supports, gaps, and graph stats
  - uses `elementId()` throughout for Neo4j 5+ compatibility

- `embeddings/store.py`
  - initializes persistent ChromaDB collections
  - provides `add_chunk()`, `add_claim()`, `find_similar_claims()`, and `find_similar_chunks()`

- `agents/planner.py`
  - builds multi-query plans from LLM output
  - handles invalid JSON and dict-form subqueries gracefully

- `agents/contradiction.py`
  - finds semantic claim pairs and classifies relationships via LLM
  - now handles Neo4j string element IDs safely

- `agents/gap_finder.py`
  - extracts cluster-based research gaps and inserts them with claim links

- `agents/coordinator_v2.py`
  - merges contexts, handles temporal questions, and loops until reflection is sufficient

---

## 4. Core Findings

### 4.1 Neo4j migration

- Neo4j has replaced the previous SQLite graph layer for new ingestion and query paths.
- `graph/neo4j_queries.py` now uses `elementId()` consistently.
- Constraints and indexes are implemented in `graph/neo4j_schema.py`.

### 4.2 Gap linking

- `insert_gap()` creates `Gap` nodes and links them to claims via `RELATED_TO` edges.
- `get_gaps()` returns `related_claims` as a list of linked claim element IDs.
- Coordinator v2 filters gaps by related claim IDs for relevance.

### 4.3 Planner hardening

- `agents/planner.py` now clamps malformed subqueries and converts dict entries into strings.
- If JSON parsing fails, the planner falls back to using the original question as the single query.
- Subqueries are limited to 3 to prevent runaway loops.

### 4.4 ChromaDB ingestion

- `embeddings/store.py` now uses `upsert()` for both `add_chunk()` and `add_claim()`.
- This fixes re-ingestion DuplicateIDError issues and makes embedding ingestion idempotent.

### 4.5 LLM provider dispatch

- `llm.py` now exposes `LLM_PROVIDER` at module level so tests can patch it safely during reload.
- Claude and Groq dispatch both work under unit test conditions.

---

## 5. Live Test Results

### 5.1 Test command executed

```bash
d:/AI-Projects/schimesh/venv/Scripts/python.exe -m pytest tests/test_aethergraph.py -v
```

### 5.2 Results

- **Tests collected:** 83
- **Passed:** 83
- **Failed:** 0
- **Warnings:** 1 DeprecationWarning from `opentelemetry` only

### 5.3 Relevant regression coverage

The suite confirms the following bug fixes:
- `agents/contradiction.py` no longer fails on Neo4j 5+ string element IDs
- `agents/reflector.py` no longer contains duplicate post-return dead code
- `embeddings/store.py` now uses idempotent `upsert()` behavior
- `llm.py` dispatch now supports test-time patched provider selection

---

## 6. Risks and Recommendations

### 6.1 Remaining risk

- `agents/coordinator.py` (legacy SQLite coordinator) still exists and can diverge from the Neo4j-backed `agents/coordinator_v2.py`.
- This is the primary architectural risk for the next phase and should be retired or isolated.

### 6.2 Recommended next steps

1. Remove or archive `agents/coordinator.py` once `coordinator_v2.py` is fully validated.
2. Add end-to-end integration tests that cover live Neo4j and Chroma ingestion flows.
3. Improve `gap_finder.py` documentation and ensure both future-work and cluster gap extraction are exercised.
4. Add a small health check for ChromaDB metadata consistency (`paper_year` as int).
5. Document the current Neo4j vs SQLite migration status in `README.md`.

---

## 7. Audit Verdict

The system is in a strong state for a v1.10 release. The new Neo4j graph backend is validated, key bug fixes are in place, and the full `tests/test_aethergraph.py` suite passes cleanly. The remaining work is mostly Phase 5 cleanup around legacy coordinator paths and stability hardening.
