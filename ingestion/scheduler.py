# ingestion/scheduler.py
"""
Continuous ingestion scheduler.

Fetches new ArXiv papers on a configurable interval (default: every 6 hours),
runs Agent 1 (Reader) on them, then triggers Agent 2 (Contradiction Detector).

Usage — embedded in Streamlit / main.py:
    from ingestion.scheduler import start_scheduler, stop_scheduler, trigger_now
    start_scheduler()

Usage — standalone:
    python ingestion/scheduler.py
"""
import time
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from config import SCHEDULER_TOPICS, SCHEDULER_INTERVAL_HOURS, SCHEDULER_PAPERS_PER_RUN
from ingestion.arxiv_client import search_papers, download_pdf
from agents.reader import process_paper
from agents.contradiction import run_contradiction_detection

# ─── Module-level state (accessible from UI thread) ──────────
_scheduler = None
_run_log: list[dict] = []   # [{timestamp, papers_added, claims_added, contradictions_found}]
_lock = threading.Lock()


# ─── Internal helpers ─────────────────────────────────────────

def _log_run(papers_added: int, claims_added: int, contradictions_found: int):
    with _lock:
        _run_log.append({
            "timestamp": datetime.now().isoformat(),
            "papers_added": papers_added,
            "claims_added": claims_added,
            "contradictions_found": contradictions_found
        })
        # Keep only the last 50 entries
        if len(_run_log) > 50:
            _run_log.pop(0)


def _on_job_event(event):
    if event.exception:
        print(f"[Scheduler] ❌ Job failed: {event.exception}")
    else:
        print(f"[Scheduler] ✅ Job completed successfully")


def _ingestion_job():
    """
    Single ingestion run. Called by the scheduler on each tick.
    Searches ArXiv for each configured topic, ingests new papers,
    then runs contradiction detection on newly added claims.
    """
    print(f"\n[Scheduler] Starting ingestion run at {datetime.now().isoformat()}")

    total_papers = 0
    total_claims = 0

    for topic in SCHEDULER_TOPICS:
        print(f"  Topic: '{topic}'")
        papers = search_papers(topic, max_results=SCHEDULER_PAPERS_PER_RUN)

        for paper in papers:
            try:
                pdf_path = download_pdf(paper["arxiv_id"])
                claims_added = process_paper(paper, pdf_path)
                total_papers += 1
                total_claims += (claims_added or 0)
            except Exception as e:
                print(f"  Warning: failed to process {paper['arxiv_id']}: {e}")

    print(f"  Running contradiction detection on new claims...")
    try:
        contradictions_found = run_contradiction_detection()
    except Exception as e:
        print(f"  Warning: contradiction detection failed: {e}")
        contradictions_found = 0

    _log_run(total_papers, total_claims, contradictions_found)
    print(
        f"[Scheduler] Run complete — "
        f"{total_papers} papers, {total_claims} claims, "
        f"{contradictions_found} contradictions"
    )


# ─── Public API ───────────────────────────────────────────────

def get_run_log() -> list[dict]:
    """Returns a copy of the ingestion run log. Thread-safe."""
    with _lock:
        return list(_run_log)


def start_scheduler() -> BackgroundScheduler:
    """
    Start the background ingestion scheduler.
    Idempotent — calling a second time returns the existing scheduler.
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        print("[Scheduler] Already running.")
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_listener(_on_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    _scheduler.add_job(
        func=_ingestion_job,
        trigger="interval",
        hours=SCHEDULER_INTERVAL_HOURS,
        id="ingestion_job",
        name="ArXiv ingestion",
        max_instances=1,           # never overlap two runs
        coalesce=True,             # if multiple missed ticks, run once
        misfire_grace_time=3600    # 1-hour grace window
    )

    _scheduler.start()
    print(
        f"[Scheduler] Started — interval: every {SCHEDULER_INTERVAL_HOURS}h, "
        f"topics: {len(SCHEDULER_TOPICS)}"
    )
    return _scheduler


def stop_scheduler():
    """Gracefully stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped.")


def trigger_now():
    """Run one ingestion job immediately, outside the normal schedule."""
    print("[Scheduler] Manual trigger...")
    _ingestion_job()


if __name__ == "__main__":
    # Standalone: run immediately, then stay on schedule
    trigger_now()
    start_scheduler()
    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()