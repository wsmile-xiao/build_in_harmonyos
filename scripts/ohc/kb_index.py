"""Knowledge graph FTS5 in-memory index (zero file output).

Builds a SQLite FTS5 index in :memory: at runtime from .kv files.
No database file is written to disk — suitable for growth-oriented,
distributed contribution workflows.

Usage:
    from .kb_index import fts_search
    results = fts_search("undefined reference to pthread_create", graph_dir)
    # → [{"id": "E003", "score": -1.23, "severity": 3}, ...]
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Optional

_STOPWORDS = frozenset({
    "the", "for", "with", "and", "not", "are", "but", "you", "all",
    "any", "can", "had", "her", "was", "one", "our", "out", "has",
    "have", "him", "his", "how", "its", "may", "new", "now", "old",
    "see", "them", "then", "this", "will", "your", "from", "that",
    "make", "error", "warning", "failed", "file", "line", "into",
    "such", "than", "them", "were", "when", "what", "been", "some",
})


def _parse_severity(val: str) -> int:
    """Extract numeric severity from possibly non-standard value."""
    m = re.search(r'\d+', val)
    return int(m.group()) if m else 0


def _extract_tokens(text: str) -> list[str]:
    """Extract meaningful query tokens from error text."""
    tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _parse_kv(path: str) -> dict[str, str]:
    """Minimal KV parser compatible with models.parse_kv_file."""
    data: dict[str, str] = {}
    current_key: Optional[str] = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("#"):
                continue
            m = re.match(r'^([a-z_]+):\s*(.*)', line)
            if m:
                current_key = m.group(1)
                data[current_key] = m.group(2).strip()
            elif current_key and line.startswith(" "):
                data[current_key] += " " + line.strip()
    return data


def _build_memory_index(graph_dir: str) -> sqlite3.Connection:
    """Build an in-memory FTS5 index from all E*.kv files.

    Automatically includes new .kv files — no rebuild step needed.
    Raises sqlite3.OperationalError if FTS5 is not available.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5("
        "id UNINDEXED, severity UNINDEXED, keywords, signature, "
        "title, category, root_cause, tokenize='unicode61');"
    )

    for fname in sorted(os.listdir(graph_dir)):
        if not re.match(r'^E\d+\.kv$', fname):
            continue
        kv_path = os.path.join(graph_dir, fname)
        data = _parse_kv(kv_path)

        keywords = data.get("match_keywords", "").replace("\n", " ").strip()
        signature = data.get("error_signature", "").replace("|", " ").strip()
        title = data.get("title", "")
        category = data.get("category", "")
        root_cause = data.get("root_cause", "")

        conn.execute(
            "INSERT INTO kb_fts (id, severity, keywords, signature, "
            "title, category, root_cause) VALUES (?,?,?,?,?,?,?)",
            (data.get("id", ""),
             _parse_severity(data.get("severity", "0")),
             keywords, signature, title, category, root_cause),
        )

    conn.commit()
    return conn


# Module-level cache (rebuilt when .kv files change)
_index_cache: Optional[sqlite3.Connection] = None
_index_mtime: float = 0


def _get_latest_mtime(graph_dir: str) -> float:
    """Get the latest mtime of any .kv file in graph_dir."""
    latest = 0.0
    for fname in os.listdir(graph_dir):
        if re.match(r'^E\d+\.kv$', fname):
            mtime = os.path.getmtime(os.path.join(graph_dir, fname))
            if mtime > latest:
                latest = mtime
    return latest


def fts_search(
    error_text: str,
    graph_dir: str,
    top_n: int = 5,
) -> list[dict]:
    """BM25 full-text search, returning top-N candidates.

    Returns [] if FTS5 unavailable or no matches.
    Each result: {"id": "E003", "score": -1.23, "severity": 3}
    (FTS5 bm25() returns negative values; closer to 0 = more relevant)
    """
    global _index_cache, _index_mtime

    # Check if index needs rebuild (new/modified .kv files)
    latest = _get_latest_mtime(graph_dir)
    if _index_cache is None or latest > _index_mtime:
        try:
            _index_cache = _build_memory_index(graph_dir)
            _index_mtime = latest
        except sqlite3.OperationalError:
            # FTS5 not available
            return []

    tokens = _extract_tokens(error_text)
    if not tokens:
        return []

    # Build FTS5 query: OR of quoted tokens
    query = " OR ".join(f'"{t}"' for t in tokens)

    try:
        rows = _index_cache.execute(
            "SELECT id, severity, bm25(kb_fts) AS score "
            "FROM kb_fts WHERE kb_fts MATCH ? "
            "ORDER BY score ASC LIMIT ?",
            (query, top_n),
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    return [{"id": r[0], "severity": r[1], "score": r[2]} for r in rows]


def fts_available() -> bool:
    """Check if FTS5 is available in this Python's sqlite3."""
    try:
        c = sqlite3.connect(":memory:")
        c.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        c.close()
        return True
    except Exception:
        return False
