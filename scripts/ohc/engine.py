"""Unified error-pattern matching engine (v3).


Five phases:
  A. index.tsv coarse filter (keyword matching + severity weight)
  B. .kv fine ranking (error_signature exact matching)
  C. Solution generation (load full .kv data)
  D. Principle filtering (lookup principles.kv for display)
  E. Formatted output (interactive / json / autofix / inline)
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

from .models import (
    ErrorEntry, IndexEntry, Principle, Severity,
    parse_error_entry, parse_index_tsv, parse_principles,
)
from .utils import graph_dir


# ═══════════════════════════════════════════════════════
# Match result
# ═══════════════════════════════════════════════════════

@dataclass
class MatchResult:
    """Output of the matching engine."""
    matched: bool = False
    match_id: str = ""
    phase_a_score: int = 0
    phase_b_score: int = 0
    total_score: int = 0
    entry: ErrorEntry | None = None
    principle_names: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# Error normalization (方案 A, inspired by FixHive)
# ═══════════════════════════════════════════════════════

_NORMALIZE_RULES = [
    # Quoted module/library names → {module} (before path rule)
    (re.compile(r"'[a-zA-Z@/_.-]+'"), "'{module}'"),
    (re.compile(r'"[a-zA-Z@/_.-]+"'), '"{module}"'),
    # Shared library names → {lib}.so.{version}
    (re.compile(r'\b([a-zA-Z_]\w+)\.so\.\d+'), r'{lib}.so.{version}'),
    # File paths → {path}
    (re.compile(r'/[\w./-]+\.\w{1,4}'), '{path}'),
    # Version numbers → {version}
    (re.compile(r'\b\d+\.\d+\.\d+\b'), '{version}'),
    (re.compile(r'\b\d+\.\d+\b'), '{version}'),
    # Line numbers → {line}
    (re.compile(r':\d+:\d+'), ':{line}'),
    (re.compile(r'line \d+'), 'line {line}'),
    # Hex addresses → {addr}
    (re.compile(r'\b0x[0-9a-fA-F]+\b'), '{addr}'),
]


def normalize_error(error_text: str) -> str:
    """Normalize error text by replacing variable parts with placeholders.

    Inspired by FixHive's signature normalization.
    Different projects/versions with the same error type produce
    the same normalized signature, boosting recall.

    Examples:
        "foo.c:42:5: error" → "{path}:{line}: error"
        "Cannot find module 'react'" → "Cannot find module {module}"
    """
    result = error_text
    for pattern, replacement in _NORMALIZE_RULES:
        result = pattern.sub(replacement, result)
    return result


# ═══════════════════════════════════════════════════════
# Phase A: Coarse filter via FTS5 BM25 (+ legacy fallback)
# ═══════════════════════════════════════════════════════

@dataclass
class _Candidate:
    entry: IndexEntry
    score: int = 0


def _phase_a(
    error_text: str,
    index_entries: list[IndexEntry],
    min_score: int = 2,
    top_n: int = 5,
    gdir: str | None = None,
) -> list[_Candidate]:
    """Scan index, score by BM25 (FTS5) with substring fallback."""
    # Try FTS5 BM25 first (reads .kv files directly, auto-includes new entries)
    if gdir:
        try:
            from .kb_index import fts_search, fts_available
            if fts_available():
                fts_results = fts_search(error_text, gdir, top_n=top_n)
                if fts_results:
                    candidates: list[_Candidate] = []
                    for r in fts_results:
                        entry = _find_entry_by_id(index_entries, r["id"])
                        if entry:
                            # BM25 score is negative; convert to positive weight
                            # Severity boost: sev3 ×3, sev2 ×2
                            raw_score = max(1, int(abs(r["score"]) * 2))
                            if entry.severity >= 3:
                                raw_score *= 3
                            elif entry.severity >= 2:
                                raw_score *= 2
                            candidates.append(_Candidate(entry=entry, score=raw_score))
                    if candidates:
                        candidates.sort(key=lambda c: c.score, reverse=True)
                        return candidates[:top_n]
        except Exception:
            pass  # Fall through to legacy

    # Legacy: substring matching on index.tsv
    return _phase_a_legacy(error_text, index_entries, min_score, top_n)


def _phase_a_dual(
    error_text: str,
    normalized: str,
    index_entries: list[IndexEntry],
    min_score: int = 2,
    top_n: int = 5,
    gdir: str | None = None,
) -> list[_Candidate]:
    """Dual matching: raw text + normalized text, merge results.

    方案 A: Entries matched by both raw and normalized text get
    extra score (double-hit boost). Entries only matched by
    normalized text still get a bonus for recall improvement.
    """
    raw_cands = _phase_a(error_text, index_entries, min_score, top_n, gdir)
    norm_cands = _phase_a(normalized, index_entries, min_score, top_n, gdir)
    _tr(f"[A] raw   top: {[(c.entry.id, c.score) for c in raw_cands]}")
    _tr(f"[A] norm  top: {[(c.entry.id, c.score) for c in norm_cands]}")

    if not raw_cands and not norm_cands:
        return []
    if not norm_cands:
        return raw_cands
    if not raw_cands:
        return norm_cands

    # Merge: raw + normalized, double-hit gets bonus
    merged: dict[str, _Candidate] = {}
    for c in raw_cands:
        merged[c.entry.id] = _Candidate(entry=c.entry, score=c.score)
    for c in norm_cands:
        if c.entry.id in merged:
            merged[c.entry.id].score += c.score  # Double-hit bonus
        else:
            merged[c.entry.id] = _Candidate(entry=c.entry, score=c.score + 2)

    result = sorted(merged.values(), key=lambda x: x.score, reverse=True)
    return result[:top_n]


def _find_entry_by_id(entries: list[IndexEntry], eid: str) -> IndexEntry | None:
    """Find an IndexEntry by ID."""
    for e in entries:
        if e.id == eid:
            return e
    return None


def _phase_a_legacy(
    error_text: str,
    index_entries: list[IndexEntry],
    min_score: int = 2,
    top_n: int = 5,
) -> list[_Candidate]:
    """Legacy substring matching (fallback when FTS5 unavailable)."""
    error_lower = error_text.lower()
    candidates: list[_Candidate] = []

    for entry in index_entries:
        if not entry.id.startswith("E"):
            continue
        if not entry.keywords:
            continue

        score = 0
        for kw in entry.keywords:
            if len(kw) < 2:
                continue
            if kw.lower() in error_lower:
                score += 1

        if entry.severity >= 3:
            score *= 3
        elif entry.severity >= 2:
            score *= 2

        if score >= min_score:
            candidates.append(_Candidate(entry=entry, score=score))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]


# ═══════════════════════════════════════════════════════
# Retrieval trace (v12.4: --trace 检索轨迹，借鉴 OpenViking 可观测检索)
# ═══════════════════════════════════════════════════════

_trace_buf: list[str] | None = None


def _tr(msg: str) -> None:
    if _trace_buf is not None:
        _trace_buf.append(msg)


# ═══════════════════════════════════════════════════════
# Phase context markers (for phase-aware score dampening)
# ═══════════════════════════════════════════════════════

_PHASE_MARKERS = {
    "download": ["download", "fetch", "AuthenticationException", "403", "Connection timed out", "could not resolve"],
    "patch": ["patch", "does not exist", "hunk failed", "patch unexpectedly"],
    "configure": ["configure", "bad interpreter", "no such file or directory", "unrecognized option"],
    "compilation": ["error:", "warning:", "undefined reference", "sockaddr_storage", "redefinition"],
    "install": ["install", "cp:", "cannot create", "permission denied"],
}


# ═══════════════════════════════════════════════════════
# Phase B: Fine ranking via .kv error_signature
# ═══════════════════════════════════════════════════════

def _phase_b(
    error_text: str,
    candidates: list[_Candidate],
    gdir: str,
    sig_bonus: int = 5,
) -> tuple[str, int, int]:
    """Load .kv for each candidate, score by error_signature matching.

    Returns (best_match_id, phase_b_score, phase_a_score).
    If no Phase B hit, falls back to Phase A top candidate.
    """
    error_lower = error_text.lower()
    best_id = ""
    best_b = 0
    best_a = 0

    # Pre-compute phase context from error text (for dampening)
    error_phase_context: set[str] = set()
    for phase, markers in _PHASE_MARKERS.items():
        for marker in markers:
            if marker.lower() in error_lower:
                error_phase_context.add(phase)
                break

    for cand in candidates:
        kv_path = os.path.join(gdir, f"{cand.entry.id}.kv")
        if not os.path.isfile(kv_path):
            continue

        raw: dict[str, str] = {}
        try:
            from .models import parse_kv_file
            raw = parse_kv_file(kv_path)
        except Exception:
            continue

        sig = raw.get("error_signature", "")
        match_score = 0

        if sig:
            for pattern in sig.split("|"):
                pattern = pattern.strip().lower()
                if pattern and pattern in error_lower:
                    match_score += sig_bonus
                    _tr(f"[B] {cand.entry.id}: signature 命中 {pattern!r} (+{sig_bonus})")
                    break  # Same as build-driver inline: first match only

        # match_keywords bonus (+1 each)
        mkw = raw.get("match_keywords", "")
        if mkw:
            for kw in mkw.split(","):
                kw = kw.strip()
                if kw and kw.lower() in error_lower:
                    match_score += 1

        # Phase context boost: dampen entries whose phase doesn't match
        # the error's phase context (pure penalty, never increases score)
        if error_phase_context and match_score > 0:
            entry_phases = set()
            if hasattr(cand.entry, 'phase') and cand.entry.phase:
                entry_phases = set(p.lower() for p in cand.entry.phase)
            if entry_phases and error_phase_context and not (entry_phases & error_phase_context):
                match_score = max(0, match_score - 2)  # dampen mismatched phase

        _tr(f"[B] {cand.entry.id}: match={match_score} (phaseA={cand.score})")
        if match_score > best_b:
            best_b = match_score
            best_id = cand.entry.id
            best_a = cand.score

    # Fallback to Phase A top candidate
    if not best_id and candidates:
        best_id = candidates[0].entry.id
        best_b = 0
        best_a = candidates[0].score

    return best_id, best_b, best_a


# ═══════════════════════════════════════════════════════
# Phase B+: Relation network expansion
# ═══════════════════════════════════════════════════════

def _phase_b_plus(
    best_id: str,
    candidates: list[_Candidate],
    gdir: str,
    index_entries: list[IndexEntry],
) -> list[_Candidate]:
    """Expand candidates via relation edges (causes, caused_by, similar_to).

    Loads the best match's .kv, reads relation fields, and adds related
    entries as low-score candidates so Phase B's regex can promote them
    if the error text also matches their signature.
    """
    kv_path = os.path.join(gdir, f"{best_id}.kv")
    if not os.path.isfile(kv_path):
        return candidates

    try:
        from .models import parse_kv_file
        raw = parse_kv_file(kv_path)
    except Exception:
        return candidates

    # Collect related IDs from all relation fields
    related_ids: set[str] = set()
    for field in ("similar_to", "caused_by", "causes"):
        val = raw.get(field, "").strip()
        if val:
            for rid in re.findall(r"E\d+", val):
                related_ids.add(rid)

    if not related_ids:
        return candidates

    # Add related entries as candidates (low score, Phase B regex can boost)
    existing_ids = {c.entry.id for c in candidates}
    _tr(f"[B+] {best_id} 关联扩展: {sorted(related_ids)}")
    for rid in sorted(related_ids):
        if rid not in existing_ids:
            entry = _find_entry_by_id(index_entries, rid)
            if entry:
                candidates.append(_Candidate(entry=entry, score=1))

    return candidates
# ═══════════════════════════════════════════════════════

def _phase_c(match_id: str, gdir: str) -> ErrorEntry | None:
    """Load the full .kv for the best match."""
    kv_path = os.path.join(gdir, f"{match_id}.kv")
    if not os.path.isfile(kv_path):
        return None
    try:
        return parse_error_entry(kv_path)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════
# Phase D: Principle filtering
# ═══════════════════════════════════════════════════════

def _phase_d(
    entry: ErrorEntry,
    principles: list[Principle],
) -> list[str]:
    """Look up principle names for the entry's principle references."""
    if not entry.principles:
        return []

    p_map = {p.id: p.name for p in principles}
    names: list[str] = []
    for pid in entry.principles:
        pid = pid.strip().strip("#").strip()
        if pid:
            names.append(p_map.get(pid, pid))
    return names


# ═══════════════════════════════════════════════════════
# Phase E: Output formatters
# ═══════════════════════════════════════════════════════

def _truncate(s: str, maxlen: int = 120) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").strip()
    return s[:maxlen - 3] + "..." if len(s) > maxlen else s


def _escape_json(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def format_interactive(result: MatchResult) -> str:
    """Human-readable interactive output (default mode)."""
    if not result.matched or not result.entry:
        return "❌ 未找到匹配的错误模式。\n"
    e = result.entry
    lines: list[str] = []
    lines.append("╔══════════════════════════════════════════════╗")
    lines.append(f"║  🎯 命中: {e.id}  (Phase B: {result.phase_b_score})")
    lines.append("╚══════════════════════════════════════════════╝")
    lines.append("")
    lines.append("📋 基本信息:")
    lines.append(f"   严重度: {int(e.severity)}  |  类别: {'|'.join(e.category)}")
    lines.append(f"   触发工具: {'|'.join(e.trigger_tool)}  |  阶段: {'|'.join(e.phase)}")
    lines.append("")
    lines.append("🔍 根因分析:")
    lines.append(f"   {e.root_cause}")
    lines.append(f"   影响范围: {e.affected_scope}")
    lines.append("")
    lines.append(f"★ 推荐方案 (优先级 {e.rec_priority}): {e.rec_approach}")
    lines.append(f"   {e.rec_description}")
    if e.rec_command:
        lines.append(f"   命令: {e.rec_command}")
    lines.append(f"   自动修复: {'true' if e.rec_auto_fix else 'false'}  |  实现: {e.rec_impl}")

    if e.fallback:
        fb = e.fallback
        lines.append("")
        lines.append(f"↩️  回退方案 (优先级 {fb.priority}): {fb.approach}")
        if fb.description:
            lines.append(f"   {fb.description}")
        if fb.command:
            lines.append(f"   命令: {fb.command}")

    if e.forbid_rules:
        lines.append("")
        lines.append("🚫 禁止做法:")
        for rule in e.forbid_rules:
            if rule.pattern:
                lines.append(f"   ❌ {rule.pattern}")
            if rule.reason:
                lines.append(f"   原因: {rule.reason}")
            if rule.consequence:
                lines.append(f"   后果: {rule.consequence}")

    if result.principle_names:
        lines.append("")
        lines.append("⚖️  原则引用:")
        for name in result.principle_names:
            lines.append(f"   ✅ {name}")

    rel = e.relations
    if any([rel.causes, rel.similar_to, rel.conflicts_with]):
        lines.append("")
        parts = []
        if rel.causes:
            parts.append(f"导致=[{','.join(rel.causes)}]")
        if rel.similar_to:
            parts.append(f"相似=[{','.join(rel.similar_to)}]")
        if rel.conflicts_with:
            parts.append(f"冲突=[{','.join(rel.conflicts_with)}]")
        lines.append(f"🔗 关联: {' '.join(parts)}")

    if e.doc_file:
        lines.append(f"📄 文档: {e.doc_file}")
    if e.verification_cmd:
        lines.append(f"✅ 验证: {_truncate(e.verification_cmd, 80)}")

    return "\n".join(lines) + "\n"


def format_json(result: MatchResult) -> str:
    """JSON output (--json mode)."""
    if not result.matched or not result.entry:
        return json.dumps({"status": "no_match"}, ensure_ascii=False, indent=2) + "\n"
    e = result.entry
    obj = {
        "status": "matched",
        "match_id": e.id,
        "phase_b_score": result.phase_b_score,
        "total_score": result.total_score,
        "severity": str(int(e.severity)),
        "category": "|".join(e.category),
        "root_cause": e.root_cause,
        "recommendation": {
            "approach": e.rec_approach,
            "description": e.rec_description,
            "command": e.rec_command or "",
            "auto_fix": e.rec_auto_fix,
            "impl": e.rec_impl,
        },
        "forbidden": {},
        "principles": ",".join(e.principles),
    }
    if e.fallback:
        obj["fallback"] = {
            "approach": e.fallback.approach,
            "description": e.fallback.description,
            "command": e.fallback.command or "",
            "auto_fix": e.fallback.auto_fix,
        }
    if e.forbid_rules and e.forbid_rules[0].pattern:
        obj["forbidden"] = {
            "pattern": e.forbid_rules[0].pattern,
            "reason": e.forbid_rules[0].reason or "",
        }
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def format_autofix(result: MatchResult) -> str:
    """Autofix command output (--autofix mode)."""
    if not result.matched or not result.entry:
        return "# ❌ 未找到匹配的错误模式\n"
    e = result.entry
    lines: list[str] = []
    lines.append(f"# === 错误模式匹配: {e.id} (severity={int(e.severity)}) ===")
    lines.append(f"# 根因: {_truncate(e.root_cause, 120)}")
    lines.append("")

    if e.rec_auto_fix and e.rec_command:
        lines.append(f"# ★ 推荐方案 (优先级 {e.rec_priority}): {e.rec_approach}")
        lines.append(e.rec_command)
    else:
        lines.append(f"# ⚠️  推荐方案需人工操作: {e.rec_approach}")
        lines.append(f"# {e.rec_description}")
        if e.fallback and e.fallback.auto_fix and e.fallback.command:
            lines.append(f"# 回退方案: {e.fallback.approach}")
            lines.append(e.fallback.command)

    if e.forbid_rules and e.forbid_rules[0].pattern:
        lines.append(f"# ❌ 禁止: {e.forbid_rules[0].pattern}")
        if e.forbid_rules[0].reason:
            lines.append(f"# 原因: {e.forbid_rules[0].reason}")

    return "\n".join(lines) + "\n"


def format_inline(result: MatchResult) -> str:
    """Inline log output (integration mode).

    This is the format printed when the engine hits a match.
    """
    if not result.matched or not result.entry:
        return ""
    e = result.entry
    lines: list[str] = []
    lines.append("  ⚠️")
    lines.append(f"  ⚠️  ═══ 🧠 知识图谱命中: {e.id} (评分:{result.total_score}) ═══")
    lines.append(f"  ⚠️  步骤: {'|'.join(e.phase)} | 方案: {e.rec_approach}")
    lines.append(f"  ⚠️  根因: {_truncate(e.root_cause, 120)}")
    if e.forbid_rules and e.forbid_rules[0].pattern:
        lines.append(f"  ⚠️  禁止: {e.forbid_rules[0].pattern}")
    lines.append("  ⚠️")
    if e.rec_auto_fix and e.rec_command:
        lines.append(f"  → 🔧 v3 自动修复: {e.rec_command}")
    if e.doc_file:
        doc_path = os.path.join(
            os.path.dirname(graph_dir()), e.doc_file
        )
        if os.path.isfile(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                doc_lines = [l.rstrip("\n") for l in f.readlines()[:40]]
            lines.append("  → --- {} 详细文档 ---".format(e.id))
            for dl in doc_lines:
                lines.append(f"  →   {dl}")
    lines.append("  ⚠️")
    lines.append("  ⚠️  ═══ 以上来自 knowledge/graph/ (v3 引擎) ═══")
    lines.append("  ⚠️")
    return "\n".join(lines) + "\n"


def _sidecar_path(gdir: str) -> str:
    return os.path.join(os.path.dirname(gdir.rstrip("/\\")),
                        ".metrics-local.json")


def _sidecar_load(path: str) -> dict:
    """读 sidecar 并归一为 v2 结构；兼容 v1 顶层 {eid: "date"}。"""
    import json
    data = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    entries = {}
    raw = data.get("entries")
    if isinstance(raw, dict):
        entries = {k: v for k, v in raw.items() if isinstance(v, dict)}
    else:
        for k, v in data.items():
            if k in ("entries", "pending"):
                continue
            if isinstance(v, str):
                entries[k] = {"last": v}
    pending = data.get("pending")
    if not isinstance(pending, list):
        pending = []
    return {"entries": entries,
            "pending": [p for p in pending if isinstance(p, str)]}


def _sidecar_save(path: str, sc: dict) -> None:
    import json
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _touch_metrics(eid: str, gdir: str) -> None:
    """v12.20: 命中记录写入本地 sidecar v2（gitignored），不写共享 .kv。

    设计修正：直接改 .kv 会让每个包 PR 携带知识文件 diff，与并发 PR
    在同一 E 条目上产生合并冲突（社区规模必现）。sidecar 本地聚合、
    零污染；kb-report 同时读 sidecar 与 .kv 遗留字段。

    v2 结构：{"entries": {eid: {"last": date, "s": n, "f": n}},
              "pending": [eid, ...]}。
    命中即入 pending，等待构建终局结算（settle_pending_outcomes）。
    """
    try:
        from datetime import date
        path = _sidecar_path(gdir)
        sc = _sidecar_load(path)
        ent = sc["entries"].setdefault(eid, {})
        ent["last"] = date.today().isoformat()
        if eid not in sc["pending"]:
            sc["pending"].append(eid)
        _sidecar_save(path, sc)
    except Exception:
        pass  # 度量回写永不阻塞匹配


def _record_outcome(eid: str, gdir: str, success: bool) -> None:
    """v12.20: 单条即时记账（auto-retry 成败），并移出 pending。

    替代 kb_metrics.record_result 直写共享 .kv 的旧路径（PR 污染）。
    """
    try:
        from datetime import date
        path = _sidecar_path(gdir)
        sc = _sidecar_load(path)
        ent = sc["entries"].setdefault(eid, {})
        ent["last"] = date.today().isoformat()
        key = "s" if success else "f"
        ent[key] = int(ent.get(key, 0)) + 1
        if eid in sc["pending"]:
            sc["pending"].remove(eid)
        _sidecar_save(path, sc)
    except Exception:
        pass


def settle_pending_outcomes(gdir: str, success: bool) -> None:
    """v12.20: 构建终局结算 —— pending 中全部命中条目按本次构建成败记账。

    driver 全绿出口 settle(True)；_emit_handoff / build_cli 失败出口
    settle(False)。幂等：pending 清空后重复调用无副作用。
    """
    try:
        from datetime import date
        path = _sidecar_path(gdir)
        sc = _sidecar_load(path)
        if not sc["pending"]:
            return
        today = date.today().isoformat()
        key = "s" if success else "f"
        for eid in sc["pending"]:
            ent = sc["entries"].setdefault(eid, {})
            ent["last"] = today
            ent[key] = int(ent.get(key, 0)) + 1
        sc["pending"] = []
        _sidecar_save(path, sc)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════
# Public API: run engine
# ═══════════════════════════════════════════════════════

def run_engine(
    error_text: str,
    project_dir: str | None = None,
    top_n: int = 5,
    sig_bonus: int = 5,
) -> MatchResult:
    """Run the full five-phase matching engine.

    Args:
        error_text: The error log text to match against.
        project_dir: Project root (auto-detected if None).
        top_n: Number of Phase A candidates to pass to Phase B.
        sig_bonus: Score bonus per error_signature hit (default 5, same as inline).

    Returns:
        MatchResult with the best match.
    """
    gdir = graph_dir(project_dir)
    if not os.path.isdir(gdir):
        return MatchResult()

    _tr(f"[engine] 输入 {len(error_text)} 字符, 索引 {len(parse_index_tsv(os.path.join(gdir, 'index.tsv'))) if os.path.isfile(os.path.join(gdir, 'index.tsv')) else 0} 条")

    # Load data
    index_file = os.path.join(gdir, "index.tsv")
    principles_file = os.path.join(gdir, "principles.kv")

    index_entries = parse_index_tsv(index_file) if os.path.isfile(index_file) else []
    principles = parse_principles(principles_file) if os.path.isfile(principles_file) else []

    if not index_entries:
        return MatchResult()

    # Phase A: coarse filter (FTS5 BM25 with legacy fallback)
    # Dual matching: raw text + normalized text (方案 A)
    normalized = normalize_error(error_text)
    candidates = _phase_a_dual(error_text, normalized, index_entries, top_n=top_n, gdir=gdir)
    if not candidates:
        return MatchResult()

    # Phase B: fine ranking
    match_id, b_score, a_score = _phase_b(error_text, candidates, gdir, sig_bonus=sig_bonus)
    if not match_id:
        return MatchResult()

    # Phase B+: relation network expansion (adds related entries as candidates)
    candidates = _phase_b_plus(match_id, candidates, gdir, index_entries)

    # Phase C: load full entry
    entry = _phase_c(match_id, gdir)
    if not entry:
        return MatchResult()

    # v12.5: 命中度量回写（知识库使用反馈闭环）
    _touch_metrics(match_id, gdir)

    # Phase D: principle lookup
    p_names = _phase_d(entry, principles)

    total = a_score + b_score
    _tr(f"[result] 选中 {match_id}: phaseA={a_score} phaseB={b_score} total={total}")
    return MatchResult(
        matched=True,
        match_id=match_id,
        phase_a_score=a_score,
        phase_b_score=b_score,
        total_score=total,
        entry=entry,
        principle_names=p_names,
    )


# ═══════════════════════════════════════════════════════
# CLI entry
# ═══════════════════════════════════════════════════════

def engine_cli(argv: list[str] | None = None) -> int:
    """CLI for: python3 -m ohc engine [options] <error_text>"""
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc engine",
        description="Knowledge graph error pattern matching engine",
    )
    parser.add_argument("error_text", nargs="?", help="Error log text to match")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--autofix", action="store_true", help="Output autofix commands")
    parser.add_argument("--inline", action="store_true", help="Output inline log format (for build-driver)")
    parser.add_argument("--list", action="store_true", help="List all error patterns")
    parser.add_argument("--show", metavar="ID", help="Show details for a specific pattern")
    parser.add_argument("--project-dir", help="Project root directory")
    parser.add_argument("--file", metavar="PATH", help="Read error text from file")
    parser.add_argument("--top-n", type=int, default=5, help="Phase A top-N candidates (default 5)")
    parser.add_argument("--trace", action="store_true",
                        help="输出检索轨迹（Phase A/B 打分明细）到 stderr，调试误匹配用")

    args = parser.parse_args(argv)

    gdir = graph_dir(args.project_dir)

    # --list mode
    if args.list:
        index_file = os.path.join(gdir, "index.tsv")
        if not os.path.isfile(index_file):
            print("❌ index.tsv not found", file=sys.stderr)
            return 1
        entries = parse_index_tsv(index_file)
        for e in entries:
            print(f"{e.id}\tsev={int(e.severity)}\t{e.approach}\t{','.join(e.keywords[:3])}")
        return 0

    # --show mode
    if args.show:
        kv_path = os.path.join(gdir, f"{args.show}.kv")
        if not os.path.isfile(kv_path):
            print(f"❌ {args.show} not found", file=sys.stderr)
            return 1
        entry = parse_error_entry(kv_path)
        # Reuse MatchResult to format
        mr = MatchResult(matched=True, match_id=entry.id, entry=entry,
                         principle_names=[])
        # Load principles for display
        p_file = os.path.join(gdir, "principles.kv")
        if os.path.isfile(p_file):
            ps = parse_principles(p_file)
            mr.principle_names = _phase_d(entry, ps)
        print(format_interactive(mr), end="")
        return 0

    # Match mode
    if not args.error_text and not args.file:
        parser.print_help(sys.stderr)
        return 2

    error_text = args.error_text or ""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            error_text = f.read()

    global _trace_buf
    if args.trace:
        _trace_buf = []
    result = run_engine(error_text, project_dir=args.project_dir, top_n=args.top_n)
    if args.trace:
        for line in _trace_buf:
            print(line, file=sys.stderr)
        _trace_buf = None

    if args.json:
        print(format_json(result), end="")
    elif args.autofix:
        print(format_autofix(result), end="")
    elif args.inline:
        out = format_inline(result)
        if out:
            print(out, end="")
    else:
        print(format_interactive(result), end="")

    return 0 if result.matched else 1
