# ingestion/progress.py
import threading
import time
from datetime import datetime

class IngestionProgressTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.status = "idle"  # idle, searching, processing, contradiction, confidence, completed, failed
            self.topic = ""
            self.limit = 0
            self.current_index = 0  # 1-based index of paper being processed
            self.current_paper_id = ""
            self.current_paper_title = ""
            self.current_step = ""
            self.papers_added = 0
            self.claims_added = 0
            self.contradictions_found = 0
            self.logs = []
            self.start_time = None
            self.elapsed_per_paper = []  # List of floats (seconds) for each fully processed paper
            self.error_message = ""

    def start(self, topic: str, limit: int):
        self.reset()
        with self.lock:
            self.status = "searching"
            self.topic = topic
            self.limit = limit
            self.start_time = time.time()
            self._add_log(f"Starting custom ingestion pipeline for topic: '{topic}' (limit: {limit} papers)")

    def update_status(self, status: str, current_step: str = ""):
        with self.lock:
            self.status = status
            if current_step:
                self.current_step = current_step
            self._add_log(f"Status changed to: {status}" + (f" ({current_step})" if current_step else ""))

    def add_log(self, message: str):
        with self.lock:
            self._add_log(message)

    def _add_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        if len(self.logs) > 200:
            self.logs.pop(0)

    def start_paper(self, index: int, arxiv_id: str, title: str):
        with self.lock:
            self.current_index = index
            self.current_paper_id = arxiv_id
            self.current_paper_title = title
            self.current_step = "Downloading PDF"
            self._add_log(f"Ingesting paper {index}/{self.limit}: [{arxiv_id}] {title[:60]}")

    def update_paper_step(self, step: str):
        with self.lock:
            self.current_step = step
            self._add_log(f"  └─ {step}")

    def finish_paper(self, elapsed: float, claims_added: int):
        with self.lock:
            self.papers_added += 1
            self.claims_added += claims_added
            self.elapsed_per_paper.append(elapsed)
            self._add_log(f"  └─ Done: extracted {claims_added} claims")

    def complete(self, contradictions_found: int):
        with self.lock:
            self.status = "completed"
            self.contradictions_found = contradictions_found
            self.current_step = "Finished"
            self.current_paper_id = ""
            self.current_paper_title = ""
            duration = time.time() - self.start_time if self.start_time else 0
            self._add_log(f"Pipeline completed successfully in {duration:.1f}s. Added {self.papers_added} papers, {self.claims_added} claims, found {contradictions_found} contradictions.")

    def fail(self, error: str):
        with self.lock:
            self.status = "failed"
            self.error_message = error
            self.current_step = "Error"
            self._add_log(f"Pipeline failed: {error}")

    def get_progress(self) -> dict:
        with self.lock:
            now = time.time()
            elapsed_total = now - self.start_time if self.start_time else 0

            # Percentage calculation
            # Stages: searching (10%), processing (10% to 80% split by papers), contradiction (85%), confidence (90%), completed (100%)
            percent = 0
            if self.status == "searching":
                percent = 10
            elif self.status == "processing":
                if self.limit > 0:
                    paper_progress = (self.current_index - 1) / self.limit
                    # processing phase spans from 15% to 80%
                    percent = int(15 + paper_progress * 65)
                else:
                    percent = 50
            elif self.status == "contradiction":
                percent = 85
            elif self.status == "confidence":
                percent = 92
            elif self.status == "completed":
                percent = 100
            elif self.status == "failed":
                percent = 0

            # Remaining time calculation (seconds)
            remaining_seconds = 0
            if self.status == "processing" and self.limit > 0:
                papers_done = len(self.elapsed_per_paper)
                papers_left = self.limit - papers_done
                if papers_done > 0:
                    avg_time = sum(self.elapsed_per_paper) / papers_done
                    remaining_seconds = avg_time * papers_left + 15 # Add constant for contradiction + recalculate
                else:
                    # Default assumption: 35 seconds per paper left + 15 sec overhead
                    remaining_seconds = 35 * papers_left + 15
            elif self.status == "contradiction":
                remaining_seconds = 10
            elif self.status == "confidence":
                remaining_seconds = 5
            elif self.status == "searching":
                remaining_seconds = 30 # Assume 30 seconds for searching + initial processing overhead

            return {
                "status": self.status,
                "topic": self.topic,
                "limit": self.limit,
                "current_index": self.current_index,
                "current_paper_id": self.current_paper_id,
                "current_paper_title": self.current_paper_title,
                "current_step": self.current_step,
                "papers_added": self.papers_added,
                "claims_added": self.claims_added,
                "contradictions_found": self.contradictions_found,
                "percent": percent,
                "remaining_seconds": int(remaining_seconds),
                "error_message": self.error_message,
                "logs": list(self.logs),
                "running": self.status not in ["idle", "completed", "failed"]
            }

# Global singleton
progress_tracker = IngestionProgressTracker()
