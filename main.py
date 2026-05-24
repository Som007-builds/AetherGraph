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
from agents.coordinator import run, format_report


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
    args = parser.parse_args()

    init_db()

    if args.mode == "ingest":
        ingest(args.query, args.n)
    elif args.mode == "contradict":
        run_contradiction_detection()
    elif args.mode == "gaps":
        run_gap_finding()
    elif args.mode == "query":
        result = run(args.query)
        print(format_report(args.query, result))


if __name__ == "__main__":
    main()