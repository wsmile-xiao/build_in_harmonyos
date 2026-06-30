"""Knowledge graph quality metrics — success_rate / fail_rate tracking.

Inspired by deadends.dev's success_rate / fail_rate concept.
Records repair-attempt outcomes and computes confidence scores for
each knowledge entry, enabling data-driven pruning of low-quality
entries.

Usage:
    from .kb_metrics import record_result, get_low_confidence_entries, get_stats

    # After a repair attempt:
    record_result(graph_dir, "E045", success=True)

    # Find candidates for pruning:
    low = get_low_confidence_entries(graph_dir, threshold=0.3)

    # Overall stats:
    stats = get_stats(graph_dir)
"""
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime

from .graph import _kv_get, _kv_set
from .models import parse_kv_file
from .utils import log_info, log_ok, log_warn


# ── Helpers ──

def _entry_path(graph_dir: str, entry_id: str) -> Path:
    """Return the .kv file path for *entry_id* under *graph_dir*."""
    return Path(graph_dir) / f"{entry_id}.kv"


def _safe_int(val: str) -> int:
    """Parse an integer from a .kv value string, returning 0 on failure."""
    try:
        return int(val.strip()) if val and val.strip() else 0
    except (ValueError, AttributeError):
        return 0


def _safe_float(val: str) -> float:
    """Parse a float from a .kv value string, returning 0.0 on failure."""
    try:
        return float(val.strip()) if val and val.strip() else 0.0
    except (ValueError, AttributeError):
        return 0.0


def _iter_kv_files(graph_dir: str):
    """Yield (Path, dict) for every E###.kv file under *graph_dir*."""
    gdir = Path(graph_dir)
    for kvf in sorted(gdir.glob("E*.kv")):
        if not re.match(r'^E\d+\.kv$', kvf.name):
            continue
        data = parse_kv_file(str(kvf))
        yield kvf, data


# ── Public API ──

def record_result(graph_dir: str, entry_id: str, success: bool) -> None:
    """Record a repair attempt result for a knowledge entry.

    Updates the following fields in the entry's .kv file:
    - metrics_success_count: success count
    - metrics_fail_count:    fail count
    - metrics_confidence:    confidence = success / (success + fail)
    - metrics_last_used:     last use timestamp

    Uses graph.py's _kv_get / _kv_set to read/write .kv files.
    If the fields don't exist yet, _kv_set appends them.
    """
    entry_id = entry_id.strip().upper()
    if not entry_id:
        return

    kv = _entry_path(graph_dir, entry_id)
    if not kv.exists():
        return

    # Read current values
    success_count = _safe_int(_kv_get(kv, "metrics_success_count"))
    fail_count = _safe_int(_kv_get(kv, "metrics_fail_count"))

    # Update counts
    if success:
        success_count += 1
    else:
        fail_count += 1

    total = success_count + fail_count
    confidence = round(success_count / total, 2) if total > 0 else 0.0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write back (non-blocking: _kv_set replaces or appends)
    _kv_set(kv, "metrics_success_count", str(success_count))
    _kv_set(kv, "metrics_fail_count", str(fail_count))
    _kv_set(kv, "metrics_confidence", f"{confidence:.2f}")
    _kv_set(kv, "metrics_last_used", now)


def get_low_confidence_entries(graph_dir: str, threshold: float = 0.3) -> list[dict]:
    """Return entries whose confidence is below *threshold*.

    Only entries with at least 3 total uses (success + fail >= 3) are
    considered, so that brand-new entries are not unfairly flagged.

    Returns:
        [{"id": "E045", "confidence": 0.20, "success": 1, "fail": 4}, ...]
    """
    results: list[dict] = []

    for kvf, data in _iter_kv_files(graph_dir):
        success = _safe_int(data.get("metrics_success_count", ""))
        fail = _safe_int(data.get("metrics_fail_count", ""))
        total = success + fail

        if total < 3:
            continue

        confidence = _safe_float(data.get("metrics_confidence", ""))
        if confidence < threshold:
            results.append({
                "id": kvf.stem,
                "confidence": confidence,
                "success": success,
                "fail": fail,
            })

    return results


def get_stats(graph_dir: str) -> dict:
    """Return overall knowledge-base statistics.

    Returns a dict with:
        total_entries:         total number of E###.kv files
        entries_with_metrics:  entries that have at least 1 recorded use
        total_uses:            sum of all success + fail counts
        overall_success_rate:  total_success / total_uses  (0.0 if no uses)
        low_confidence_count:  entries below default threshold (0.3, ≥3 uses)
        never_used_count:      entries with zero recorded uses
    """
    total_entries = 0
    entries_with_metrics = 0
    total_uses = 0
    total_success = 0
    total_fail = 0
    never_used_count = 0

    for _kvf, data in _iter_kv_files(graph_dir):
        total_entries += 1

        success = _safe_int(data.get("metrics_success_count", ""))
        fail = _safe_int(data.get("metrics_fail_count", ""))
        total = success + fail

        if total > 0:
            entries_with_metrics += 1
            total_uses += total
            total_success += success
            total_fail += fail
        else:
            never_used_count += 1

    overall_success_rate = (
        round(total_success / total_uses, 2) if total_uses > 0 else 0.0
    )
    low_confidence = get_low_confidence_entries(graph_dir)

    return {
        "total_entries": total_entries,
        "entries_with_metrics": entries_with_metrics,
        "total_uses": total_uses,
        "overall_success_rate": overall_success_rate,
        "low_confidence_count": len(low_confidence),
        "never_used_count": never_used_count,
    }
