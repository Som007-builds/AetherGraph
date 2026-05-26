# utils/metrics.py
"""
In-process metrics collector for AXION.

No external service required — all data lives in memory for the process
lifetime and is exposed via the /api/metrics endpoint.

Architecture note:
    This is designed to be drop-in replaceable with Prometheus counters or
    OpenTelemetry spans. The public API (record_*, get_summary) would remain
    identical; only the backing store would change.

Usage:
    from utils.metrics import metrics

    metrics.record_llm_call("groq", duration_ms=1250, success=True)
    metrics.record_ingestion(papers=3, claims=24, failures=1)
    metrics.record_contradiction(found=7, sub_type="DIRECT_CONTRADICTION")
    metrics.record_graph_write(duration_ms=45)

    summary = metrics.get_summary()
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class MetricsCollector:
    """Thread-safe in-process metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        # LLM call metrics
        self.llm_calls_total:     int   = 0
        self.llm_calls_success:   int   = 0
        self.llm_calls_failed:    int   = 0
        self.llm_total_latency_ms: float = 0.0
        self.rate_limit_events:   int   = 0
        self.provider_calls: dict[str, int] = defaultdict(int)

        # Ingestion metrics
        self.ingestion_runs:      int   = 0
        self.papers_ingested:     int   = 0
        self.claims_extracted:    int   = 0
        self.ingestion_failures:  int   = 0

        # Contradiction metrics
        self.contradictions_found: int  = 0
        self.contradiction_types: dict[str, int] = defaultdict(int)
        self.supports_found:      int   = 0

        # Graph write metrics
        self.graph_writes_total:  int   = 0
        self.graph_total_write_ms: float = 0.0

        # Process start time
        self._started_at: float = time.time()

    # ── LLM ──────────────────────────────────────────────────────────────────

    def record_llm_call(
        self,
        provider: str,
        duration_ms: float,
        success: bool = True,
        rate_limited: bool = False,
    ) -> None:
        with self._lock:
            self.llm_calls_total += 1
            self.provider_calls[provider] += 1
            self.llm_total_latency_ms += duration_ms
            if success:
                self.llm_calls_success += 1
            else:
                self.llm_calls_failed += 1
            if rate_limited:
                self.rate_limit_events += 1

    def record_rate_limit(self, provider: str) -> None:
        with self._lock:
            self.rate_limit_events += 1
            # provider_calls is not incremented here — the retry will do that

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def record_ingestion(
        self,
        papers: int = 0,
        claims: int = 0,
        failures: int = 0,
    ) -> None:
        with self._lock:
            self.ingestion_runs += 1
            self.papers_ingested += papers
            self.claims_extracted += claims
            self.ingestion_failures += failures

    # ── Contradiction ─────────────────────────────────────────────────────────

    def record_contradiction(
        self,
        found: int = 1,
        sub_type: str = "UNKNOWN",
    ) -> None:
        with self._lock:
            self.contradictions_found += found
            self.contradiction_types[sub_type] += found

    def record_support(self, found: int = 1) -> None:
        with self._lock:
            self.supports_found += found

    # ── Graph ────────────────────────────────────────────────────────────────

    def record_graph_write(self, duration_ms: float) -> None:
        with self._lock:
            self.graph_writes_total += 1
            self.graph_total_write_ms += duration_ms

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        with self._lock:
            total_llm = self.llm_calls_total
            avg_latency = (
                round(self.llm_total_latency_ms / total_llm, 1)
                if total_llm > 0 else 0.0
            )

            total_writes = self.graph_writes_total
            avg_write = (
                round(self.graph_total_write_ms / total_writes, 1)
                if total_writes > 0 else 0.0
            )

            uptime_s = int(time.time() - self._started_at)
            hours, rem = divmod(uptime_s, 3600)
            mins, secs = divmod(rem, 60)

            return {
                "uptime": f"{hours}h {mins}m {secs}s",
                "uptime_seconds": uptime_s,

                "llm": {
                    "calls_total":     total_llm,
                    "calls_success":   self.llm_calls_success,
                    "calls_failed":    self.llm_calls_failed,
                    "avg_latency_ms":  avg_latency,
                    "rate_limit_events": self.rate_limit_events,
                    "by_provider":     dict(self.provider_calls),
                },

                "ingestion": {
                    "runs":     self.ingestion_runs,
                    "papers":   self.papers_ingested,
                    "claims":   self.claims_extracted,
                    "failures": self.ingestion_failures,
                },

                "contradictions": {
                    "found":    self.contradictions_found,
                    "supports": self.supports_found,
                    "by_type":  dict(self.contradiction_types),
                },

                "graph": {
                    "writes_total":   total_writes,
                    "avg_write_ms":   avg_write,
                },
            }


# Global singleton — import and use directly
metrics = MetricsCollector()
