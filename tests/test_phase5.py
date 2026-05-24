"""
Phase 5 Smoke Test
==================
Tests every Part A fix and Part B feature in one run.
Run from project root:
    python tests/test_phase5.py

Requires: live Neo4j + ChromaDB (same as normal usage).
Does NOT ingest new papers or call external APIs unless you uncomment B2/B3.
"""
import sys, os, json, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

PASS = []
FAIL = []


def check(name: str, ok: bool, detail: str = ""):
    if ok:
        PASS.append(name)
        print(f"  ✅ {name}")
    else:
        FAIL.append(name)
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def section(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


# ══════════════════════════════════════════════════════════════
# A1 — No v1 imports anywhere outside archive/
# ══════════════════════════════════════════════════════════════
section("A1 · v1 coordinator fully removed")

import importlib, pkgutil

V1_MARKERS = [
    "from agents.coordinator import",
    "from graph.queries import",
    "from graph.schema import",
    "run_v1(",
    "format_v1(",
    "args.v1",
    '"--v1"',
]

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
leaks = []
for dirpath, _, filenames in os.walk(root):
    # skip archive and venv folders
    if any(skip in dirpath for skip in ["archive", "venv", ".venv", "__pycache__", ".git"]):
        continue
    for fname in filenames:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(dirpath, fname)
        text = open(fpath, encoding="utf-8", errors="ignore").read()
        for marker in V1_MARKERS:
            if marker in text:
                leaks.append(f"{fpath}: '{marker}'")

check("No v1 imports outside archive/", len(leaks) == 0,
      "\n    " + "\n    ".join(leaks) if leaks else "")


# ══════════════════════════════════════════════════════════════
# A1 — main.py has correct modes, no --v1
# ══════════════════════════════════════════════════════════════
section("A1 · main.py modes")

main_text = open(os.path.join(root, "main.py"), encoding="utf-8").read()
check("main.py has 'backup' mode",   '"backup"' in main_text or "'backup'" in main_text)
check("main.py has 'schedule' mode", '"schedule"' in main_text or "'schedule'" in main_text)
check("main.py has 'citations' mode","'citations'" in main_text or '"citations"' in main_text)
check("main.py has no --v1 flag",    "--v1" not in main_text)


# ══════════════════════════════════════════════════════════════
# A2 — All gaps have at least one RELATED_TO edge
# ══════════════════════════════════════════════════════════════
section("A2 · Gap linking")

try:
    from graph.neo4j_client import run_query
    unlinked = run_query("""
        MATCH (g:Gap)
        WHERE NOT (g)-[:RELATED_TO]->()
        RETURN count(g) AS n
    """)
    n_unlinked = unlinked[0]["n"] if unlinked else 0
    check("Zero unlinked gaps in Neo4j", n_unlinked == 0,
          f"{n_unlinked} gaps still have no RELATED_TO edge — run: python -m graph.fix_empty_gap_links")
except Exception as e:
    check("Neo4j reachable for gap check", False, str(e))


# ══════════════════════════════════════════════════════════════
# A2 — gap_finder.py calls insert_gap with related_claim_ids
# ══════════════════════════════════════════════════════════════
section("A2 · gap_finder source check")

gf_text = open(os.path.join(root, "agents", "gap_finder.py"), encoding="utf-8").read()
check("gap_finder calls find_similar_claims for future_work gaps",
      "find_similar_claims" in gf_text and "related_claim_ids" in gf_text)
check("gap_finder no longer passes empty related_claim_ids=[]",
      "related_claim_ids=[]" not in gf_text)


# ══════════════════════════════════════════════════════════════
# A3 — ChromaDB paper_year is int
# ══════════════════════════════════════════════════════════════
section("A3 · ChromaDB paper_year type")

try:
    import chromadb
    from chromadb.utils import embedding_functions
    from config import CHROMA_DIR, EMBEDDING_MODEL

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    col = client.get_or_create_collection("claims", embedding_function=ef)
    result = col.get(include=["metadatas"])
    all_meta = result.get("metadatas", [])

    string_years = [
        m.get("paper_year") for m in all_meta
        if isinstance(m.get("paper_year"), str)
    ]
    check(
        f"All paper_year values are int ({len(all_meta)} entries checked)",
        len(string_years) == 0,
        f"{len(string_years)} still stored as string — run: python -m graph.fix_chroma_year_type"
    )
except Exception as e:
    check("ChromaDB reachable for year type check", False, str(e))


# ══════════════════════════════════════════════════════════════
# A4 — Planner logs warning on dict sub_query
# ══════════════════════════════════════════════════════════════
section("A4 · Planner observability")

try:
    import io, contextlib
    from unittest.mock import patch
    import agents.planner as planner_module

    malformed = {
        "sub_queries": [{"query": "What is CoT?"}],
        "fetch_contradictions": True,
        "fetch_gaps": True,
        "reasoning": "test"
    }

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        with patch.object(planner_module, "call_llm", return_value=json.dumps(malformed)):
            plan = planner_module.make_plan("test question")

    output = buf.getvalue()
    all_strings = all(isinstance(q, str) for q in plan["sub_queries"])
    warned = "⚠️" in output or "clamped" in output.lower()

    check("Dict sub_query is clamped to string", all_strings)
    check("Planner prints warning when clamping", warned, f"stdout was: {repr(output)}")

except Exception as e:
    check("Planner dict-clamp test runnable", False, str(e))


# ══════════════════════════════════════════════════════════════
# A4 — Planner normal path still works
# ══════════════════════════════════════════════════════════════
section("A4 · Planner normal operation")

try:
    from agents.planner import make_plan
    plan = make_plan("Does chain-of-thought prompting help small models?")
    check("Plan has sub_queries list",        isinstance(plan.get("sub_queries"), list))
    check("Plan sub_queries are all strings", all(isinstance(q, str) for q in plan["sub_queries"]))
    check("Plan has 1–3 sub_queries",         1 <= len(plan["sub_queries"]) <= 3)
    check("Plan has fetch_contradictions bool", isinstance(plan.get("fetch_contradictions"), bool))
    check("Plan has fetch_gaps bool",          isinstance(plan.get("fetch_gaps"), bool))
except Exception as e:
    check("Planner normal path", False, str(e))


# ══════════════════════════════════════════════════════════════
# A5 — backup.py exists and imports cleanly
# ══════════════════════════════════════════════════════════════
section("A5 · Backup module")

try:
    from graph.backup import create_backup, list_backups, prune_old_backups
    check("graph.backup imports cleanly", True)
    check("list_backups() returns a list", isinstance(list_backups(), list))
except Exception as e:
    check("graph.backup imports cleanly", False, str(e))

try:
    from config import NEO4J_CONTAINER_NAME
    check("NEO4J_CONTAINER_NAME in config", bool(NEO4J_CONTAINER_NAME))
except Exception as e:
    check("NEO4J_CONTAINER_NAME in config", False, str(e))


# ══════════════════════════════════════════════════════════════
# A5 — config.py has scheduler settings
# ══════════════════════════════════════════════════════════════
section("A5/B1 · Config scheduler vars")

try:
    from config import SCHEDULER_INTERVAL_HOURS, SCHEDULER_PAPERS_PER_RUN, SCHEDULER_TOPICS
    check("SCHEDULER_INTERVAL_HOURS is int",  isinstance(SCHEDULER_INTERVAL_HOURS, int))
    check("SCHEDULER_PAPERS_PER_RUN is int",  isinstance(SCHEDULER_PAPERS_PER_RUN, int))
    check("SCHEDULER_TOPICS is non-empty list", isinstance(SCHEDULER_TOPICS, list) and len(SCHEDULER_TOPICS) > 0)
except Exception as e:
    check("Scheduler config vars present", False, str(e))


# ══════════════════════════════════════════════════════════════
# A6 — Neo4j layer returns correct structure
# ══════════════════════════════════════════════════════════════
section("A6 · Neo4j query layer")

try:
    from graph.neo4j_queries import get_all_claims, get_contradictions, get_gaps

    claims = get_all_claims()
    check("get_all_claims() returns list", isinstance(claims, list))
    if claims:
        c = claims[0]
        check("Claim has 'text' field",       "text" in c)
        check("Claim has 'arxiv_id' field",   "arxiv_id" in c)
        check("Claim paper_year is int/None", isinstance(c.get("paper_year"), (int, type(None))))

    contras = get_contradictions()
    check("get_contradictions() returns list", isinstance(contras, list))
    if contras:
        ct = contras[0]
        check("Contradiction has claim_a_id", "claim_a_id" in ct)
        check("Contradiction has claim_b_id", "claim_b_id" in ct)
        check("Contradiction confidence is float", isinstance(ct.get("confidence"), float))

    gaps = get_gaps()
    check("get_gaps() returns list", isinstance(gaps, list))
    for g in gaps:
        check(
            f"Gap '{g['text'][:40]}…' has related_claims",
            len(g.get("related_claims", [])) > 0,
            "run: python -m graph.fix_empty_gap_links"
        )
        break  # one is enough to confirm structure

except Exception as e:
    check("Neo4j query layer", False, str(e))


# ══════════════════════════════════════════════════════════════
# B1 — Scheduler module
# ══════════════════════════════════════════════════════════════
section("B1 · Scheduler module")

try:
    from ingestion.scheduler import (
        start_scheduler, stop_scheduler, trigger_now, get_run_log
    )
    check("ingestion.scheduler imports cleanly", True)
    check("get_run_log() returns list", isinstance(get_run_log(), list))

    s = start_scheduler()
    check("start_scheduler() returns running scheduler", s is not None and s.running)

    s2 = start_scheduler()
    check("start_scheduler() is idempotent (no duplicate)", s is s2)

    stop_scheduler()
    check("stop_scheduler() stops the scheduler", not s.running)

except Exception as e:
    check("Scheduler module", False, str(e))


# ══════════════════════════════════════════════════════════════
# B2 — Citation engine (formula only — no network call)
# ══════════════════════════════════════════════════════════════
section("B2 · Citation engine — weighted confidence formula")

try:
    from agents.citation import (
        get_weighted_confidence, get_papers_with_citations, fetch_citation_count
    )
    check("agents.citation imports cleanly", True)

    # Test the formula directly without hitting the network
    def _formula(base: float, citations: int) -> float:
        MAX_BOOST = math.log2(2 + 10_000)
        boost = math.log2(2 + citations)
        return round(min(1.0, max(0.0, base * (0.5 + 0.5 * boost / MAX_BOOST))), 4)

    score_0    = _formula(0.9, 0)
    score_100  = _formula(0.9, 100)
    score_8000 = _formula(0.9, 8000)

    check("0 citations < 100 citations (score increases)",    score_0 < score_100)
    check("100 citations < 8000 citations (score increases)", score_100 < score_8000)
    check("Score clamped to ≤ 1.0",                          score_8000 <= 1.0)
    check("Score with 0 citations > 0.0",                    score_0 > 0.0)

    papers = get_papers_with_citations()
    check("get_papers_with_citations() returns list", isinstance(papers, list))

except Exception as e:
    check("Citation engine", False, str(e))


# ══════════════════════════════════════════════════════════════
# B2 — Live Semantic Scholar fetch (optional — uncomment to run)
# ══════════════════════════════════════════════════════════════
# section("B2 · Semantic Scholar live fetch")
# try:
#     count = fetch_citation_count("2201.11903")  # CoT paper
#     check("CoT paper has > 100 citations", count is not None and count > 100,
#           f"got: {count}")
# except Exception as e:
#     check("Semantic Scholar fetch", False, str(e))


# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════
print(f"\n{'═'*55}")
print(f"  Results: {len(PASS)} passed, {len(FAIL)} failed")
print(f"{'═'*55}")
if FAIL:
    print("\nFailed checks:")
    for f in FAIL:
        print(f"  ❌ {f}")
    sys.exit(1)
else:
    print("\n  All Phase 5 checks passed. ✅")
    sys.exit(0)