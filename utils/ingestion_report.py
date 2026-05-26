# utils/ingestion_report.py
"""
Pretty-print ingestion summary reports to the terminal.

Used by main.py after each CLI ingestion run to summarise what happened,
what was skipped, and why.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def print_ingestion_summary(summary: dict, elapsed: float | None = None) -> None:
    """
    Print a formatted ingestion summary report.

    Expected summary keys:
        total    (int) — papers attempted
        succeeded (int) — papers fully processed
        failed   (int) — papers that raised an exception
        skipped  (int, optional) — papers skipped (already in graph)
        failures (list[dict]) — [{arxiv_id, reason}]
        claims_per_paper (dict, optional) — {arxiv_id: int}
    """
    total     = summary.get("total", 0)
    succeeded = summary.get("succeeded", 0)
    failed    = summary.get("failed", 0)
    skipped   = summary.get("skipped", 0)
    failures  = summary.get("failures", [])
    claims_pp = summary.get("claims_per_paper", {})
    total_claims = summary.get("total_claims", 0)

    bar_width = 40
    ok_width  = int(bar_width * (succeeded / max(total, 1)))
    ok_bar    = "█" * ok_width + "░" * (bar_width - ok_width)

    sep = "─" * 60

    print(f"\n{sep}")
    print("  AXION INGESTION SUMMARY")
    print(sep)
    print(f"  Papers attempted : {total}")
    print(f"  ✅ Succeeded      : {succeeded}")
    if skipped:
        print(f"  ⏭  Skipped        : {skipped}  (already in graph)")
    print(f"  ❌ Failed         : {failed}")
    print(f"  📄 Claims added  : {total_claims}")
    if elapsed is not None:
        mins, secs = divmod(int(elapsed), 60)
        print(f"  ⏱  Elapsed        : {mins}m {secs}s")
    print(f"\n  Progress  [{ok_bar}]  {succeeded}/{total}")

    if claims_pp:
        print(f"\n  Claims per paper:")
        for arxiv_id, count in sorted(claims_pp.items(), key=lambda x: -x[1]):
            bar = "▪" * min(count, 20)
            print(f"    {arxiv_id:<22}  {bar}  ({count})")

    if failures:
        print(f"\n  Failed papers:")
        for f in failures:
            reason = (f.get("reason") or "unknown error")[:80]
            print(f"    ✗ [{f.get('arxiv_id', '?')}]  {reason}")

    print(sep)


def build_summary(
    papers: list[dict],
    results: list[dict],
    start_time: float,
) -> dict:
    """
    Build a summary dict from a list of per-paper results.

    Each result dict should have:
        arxiv_id  (str)
        success   (bool)
        claims    (int)
        error     (str | None)
    """
    succeeded = [r for r in results if r.get("success")]
    failed    = [r for r in results if not r.get("success")]

    claims_pp = {r["arxiv_id"]: r.get("claims", 0) for r in succeeded}

    return {
        "total":          len(papers),
        "succeeded":      len(succeeded),
        "failed":         len(failed),
        "skipped":        0,
        "total_claims":   sum(r.get("claims", 0) for r in succeeded),
        "claims_per_paper": claims_pp,
        "failures":       [
            {"arxiv_id": r["arxiv_id"], "reason": r.get("error", "unknown")}
            for r in failed
        ],
        "elapsed":        time.time() - start_time,
    }
