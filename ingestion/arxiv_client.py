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


def download_pdf(arxiv_id: str, max_retries: int = 3) -> Path:
    pdf_path = PAPERS_DIR / f"{arxiv_id}.pdf"

    if pdf_path.exists():
        logger.info(f"  Already downloaded: {arxiv_id}")
        return pdf_path

    import urllib.request
    import socket

    url = f"https://arxiv.org/pdf/{arxiv_id}"
    logger.info(f"  Downloading {arxiv_id}…")

    # Phase 2: retry with exponential backoff and socket timeout
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            # Set a global socket timeout for this download
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)
            try:
                urllib.request.urlretrieve(url, str(pdf_path))
            finally:
                socket.setdefaulttimeout(old_timeout)

            time.sleep(1)
            return pdf_path

        except Exception as exc:
            last_exc = exc
            # Remove partial file to prevent corruption on next run
            if pdf_path.exists():
                try:
                    pdf_path.unlink()
                except OSError:
                    pass
            if attempt < max_retries - 1:
                delay = 2 ** attempt          # 1s, 2s, 4s
                logger.warning(
                    f"  Download failed ({arxiv_id}), "
                    f"retry {attempt + 1}/{max_retries} in {delay}s: {exc}"
                )
                time.sleep(delay)
            else:
                logger.error(f"  Download failed after {max_retries} attempts: {arxiv_id}")

    raise RuntimeError(
        f"Could not download PDF for {arxiv_id} after {max_retries} attempts"
    ) from last_exc