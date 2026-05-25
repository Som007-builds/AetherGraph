import arxiv as arxiv_lib
import time
from pathlib import Path
import logging
from config import PAPERS_DIR

logger = logging.getLogger(__name__)

def search_papers(query: str, max_results: int = 20) -> list[dict]:
    client = arxiv_lib.Client()
    search = arxiv_lib.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv_lib.SortCriterion.SubmittedDate,
        sort_order=arxiv_lib.SortOrder.Descending,
    )
    
    papers = []
    for result in client.results(search):
        papers.append({
            "arxiv_id": result.entry_id.split("/")[-1],
            "title": result.title,
            "authors": [str(a) for a in result.authors],
            "abstract": result.summary,
            "published": str(result.published.date()),
            "url": result.pdf_url,
        })
        time.sleep(0.5)
    
    return papers


def download_pdf(arxiv_id: str) -> Path:
    pdf_path = PAPERS_DIR / f"{arxiv_id}.pdf"
    
    if pdf_path.exists():
        logger.info(f"  Already downloaded: {arxiv_id}")
        return pdf_path

    import urllib.request
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    logger.info(f"  Downloading {arxiv_id}...")
    urllib.request.urlretrieve(url, str(pdf_path))
    time.sleep(1)
    
    return pdf_path