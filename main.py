"""
SciMesh — entry point.
Usage: python main.py --mode [ingest|contradict|gaps|query]
"""
import argparse
from graph.schema import init_db
from ingestion.arxiv_client import search_papers, download_pdf
from agents.reader import process_paper
from agents.contradiction import run_contradiction_detection
from agents.gap_finder import run_gap_finding
from agents.coordinator import run as run_v1, format_report as format_v1
from agents.coordinator_v2 import run as run_v2


def ingest(query: str, n: int):
    print(f"Ingesting {n} papers on: {query}")
    papers = search_papers(query, max_results=n)
    for p in papers:
        pdf = download_pdf(p["arxiv_id"])
        process_paper(p, pdf)


def main():
    parser = argparse.ArgumentParser(description="SciMesh CLI")
    parser.add_argument("--mode", choices=["ingest", "contradict", "gaps", "query"], required=True)
    parser.add_argument("--query", type=str, default="chain of thought prompting LLM")
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--v1", action="store_true", help="Use v1 coordinator (single-pass)")
    args = parser.parse_args()

    init_db()

    if args.mode == "ingest":
        ingest(args.query, args.n)
    elif args.mode == "contradict":
        run_contradiction_detection()
    elif args.mode == "gaps":
        run_gap_finding()
    elif args.mode == "query":
        if args.v1:
            result = run_v1(args.query)
            print(format_v1(args.query, result))
        else:
            output = run_v2(args.query, verbose=True)
            print(output["report"])


if __name__ == "__main__":
    main()