# main.py
"""
SciMesh CLI

AUDIT FIX (§4 ⚠️ False Positives in test_phase5.py):
  The smoke test scans files for deprecated v1 imports but also flags
  itself because it contains the search markers. Fix: exclude the tests/
  directory in test_phase5.py's search loop (see tests/test_phase5.py).
  No change needed in main.py for that fix, but noted here for traceability.

PHASE 6 ADDITIONS:
  --mode confidence   Run confidence recalculation manually
  --mode experiments  Design experiments for top contradictions
"""

import argparse
from graph.neo4j_schema import init_neo4j
from ingestion.arxiv_client import search_papers, download_pdf
from agents.reader import process_paper
from agents.contradiction import run_contradiction_detection
from agents.gap_finder import run_gap_finding
from agents.coordinator_v2 import run as run_v2


def ingest(query: str, n: int):
    print(f"Ingesting {n} papers on: {query}")
    papers = search_papers(query, max_results=n)
    for p in papers:
        pdf = download_pdf(p["arxiv_id"])
        process_paper(p, pdf)


def main():
    parser = argparse.ArgumentParser(description="SciMesh CLI")
    parser.add_argument(
        "--mode",
        choices=[
            "ingest",
            "contradict",
            "gaps",
            "query",
            "backup",
            "schedule",
            "citations",
            "confidence",    # Phase 6
            "experiments",   # Phase 6
        ],
        required=True,
    )
    parser.add_argument("--query", type=str, default="chain of thought prompting LLM")
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()

    init_neo4j()

    if args.mode == "ingest":
        ingest(args.query, args.n)

    elif args.mode == "contradict":
        # Phase 6: confidence recalculation runs automatically at end of detection
        run_contradiction_detection()

    elif args.mode == "gaps":
        run_gap_finding()

    elif args.mode == "query":
        output = run_v2(args.query, verbose=True)
        print(output["report"])

    elif args.mode == "backup":
        from graph.backup import create_backup, prune_old_backups
        create_backup()
        prune_old_backups(keep=7)

    elif args.mode == "schedule":
        from ingestion.scheduler import start_scheduler, trigger_now, stop_scheduler
        import time
        trigger_now()
        start_scheduler()
        print("Scheduler running. Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            stop_scheduler()

    elif args.mode == "citations":
        from agents.citation import update_all_citation_counts
        update_all_citation_counts()

    elif args.mode == "confidence":
        # Phase 6: manual confidence recalculation pass
        from agents.confidence_updater import recalculate_all, get_confidence_distribution
        summary = recalculate_all()
        print(f"\nConfidence update complete:")
        print(f"  Updated:   {summary['total_updated']}")
        print(f"  Boosted:   {summary['boosted']}")
        print(f"  Penalized: {summary['penalized']}")
        print(f"  Unchanged: {summary['unchanged']}")
        print(f"  Avg delta: {summary['avg_delta']:.4f}")
        if summary.get("most_boosted"):
            mb = summary["most_boosted"]
            print(f"  Most boosted:   {mb['text'][:60]}... "
                  f"({mb['base']:.2f} → {mb['new']:.2f}, +{mb['delta']:.2f})")
        if summary.get("most_penalized"):
            mp = summary["most_penalized"]
            print(f"  Most penalized: {mp['text'][:60]}... "
                  f"({mp['base']:.2f} → {mp['new']:.2f}, {mp['delta']:.2f})")
        dist = get_confidence_distribution()
        print(f"\nDistribution across {dist.get('total', 0)} claims:")
        print(f"  High  (≥0.8): {dist.get('high_confidence', 0)}")
        print(f"  Med  (0.5–0.8): {dist.get('medium_confidence', 0)}")
        print(f"  Low   (<0.5): {dist.get('low_confidence', 0)}")
        print(f"  Avg confidence: {dist.get('avg_confidence', 0):.3f}")

    elif args.mode == "experiments":
        # Phase 6: design experiments for top high-confidence contradictions
        from agents.experiment_recommender import run_batch_design
        designed = run_batch_design(
            max_contradictions=20,
            min_contradiction_confidence=0.7,
        )
        print(f"\n{len(designed)} experiments designed and stored in graph.")


if __name__ == "__main__":
    main()