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
        choices=["ingest", "contradict", "gaps", "query", "backup", "schedule", "citations"],
        required=True
    )
    parser.add_argument("--query", type=str, default="chain of thought prompting LLM")
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()

    init_neo4j()

    if args.mode == "ingest":
        ingest(args.query, args.n)

    elif args.mode == "contradict":
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
        trigger_now()          # run immediately on start
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


if __name__ == "__main__":
    main()