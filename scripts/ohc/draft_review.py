"""draft_review — 草稿预审辅助工具（v12.4）

定位（用户约束）: 草稿仍按原有方式产生与人工审核纳入，本工具只输出
"预审报告" 加速人工判断——三态建议(skip-merge/create/灰区)仅供参考，
是否纳入正式知识库由人工审核决定（promote 决策权在人）。

相似度算法（纯标准库，零 LLM / 零向量）:
  1. SQLite FTS5 BM25 粗筛（复用 engine Phase A 思路，内存临时表）
  2. 精排: error_signature 字面量子串双向包含 + match_keywords Jaccard
     + category(归一化后) 重叠 + phase 重叠
  3. 三态: >=0.55 merge-into / 0.30-0.55 review-similar / <0.30 create

用法:
  python3 scripts/ohc-run.py draft-review                 # 全量草稿预审报告
  python3 scripts/ohc-run.py draft-review DRAFT-2045      # 单份详情
  python3 scripts/ohc-run.py draft-review --json          # 机器可读输出
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .models import parse_index_tsv, parse_kv_file
from .utils import log_info, log_warn, log_ok, log_fail
from .kb_taxonomy import normalize_category

_MERGE_TH = 0.55
_REVIEW_TH = 0.30


def _literal_fragments(sig: str) -> list[str]:
    """从 error_signature（| 分隔的正则）提取字面量子串，用于相似度比较。"""
    frags = []
    for pat in sig.split("|"):
        # 去掉常见正则元字符与转义，保留字母数字/下划线/连字符/点/斜杠的字面段
        lit = re.sub(r"[\\^\$\(\)\[\]\{\}\*\+\?\.\|]", " ", pat)
        for piece in lit.split():
            if len(piece) >= 5:  # 过短片段无判别力
                frags.append(piece.lower())
    return frags


def _kw_set(raw: str) -> set[str]:
    return {k.strip().lower() for k in re.split(r"[,|]", raw) if k.strip() and len(k.strip()) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse_simple_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.split("\n"):
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or line[:1] in (" ", "\t"):
            continue
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m and m.group(1) not in fields:
            fields[m.group(1)] = m.group(2).strip()
    return fields


def _load_formal(gdir: Path) -> list[dict[str, str]]:
    entries = []
    index_path = gdir / "index.tsv"
    if index_path.exists():
        for e in parse_index_tsv(str(index_path)):
            entries.append({
                "id": e.id,
                "keywords": ",".join(e.keywords),
                "category": ",".join(e.category),
                "phase": ",".join(e.phase),
            })
    return entries


def _fts_search(query: str, formal: list[dict], top_n: int) -> list[str]:
    """内存 FTS5 BM25 粗筛，返回候选 id 列表。"""
    if not query.strip() or not formal:
        return []
    try:
        db = sqlite3.connect(":memory:")
        db.execute("CREATE VIRTUAL TABLE kb USING fts5(id UNINDEXED, body)")
        db.executemany(
            "INSERT INTO kb VALUES (?, ?)",
            [(e["id"], f"{e['keywords']} {e['category']}") for e in formal],
        )
        terms = [w for w in re.split(r"[^A-Za-z0-9_+-]+", query.lower()) if len(w) >= 3][:16]
        if not terms:
            return []
        match = " OR ".join(f'"{t}"' for t in terms)
        rows = db.execute(
            "SELECT id, bm25(kb) FROM kb WHERE kb MATCH ? ORDER BY bm25(kb) LIMIT ?",
            (match, top_n * 2),
        ).fetchall()
        db.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def score_similarity(draft: dict[str, str], cand: dict[str, str], cand_kv: dict[str, str]) -> tuple[float, dict[str, object]]:
    """返回 (总分 0-1, 证据明细)。"""
    d_frags = _literal_fragments(draft.get("error_signature", ""))
    c_frags = _literal_fragments(cand_kv.get("error_signature", ""))
    frag_overlap = 0.0
    if d_frags and c_frags:
        shared = set(d_frags) & set(c_frags)
        frag_overlap = len(shared) / min(len(d_frags), len(c_frags))
        # 子串包含（草稿片段出现在候选 signature 文本中）
        c_text = cand_kv.get("error_signature", "").lower()
        contained = sum(1 for f in d_frags if f in c_text) / len(d_frags)
        frag_overlap = max(frag_overlap, contained * 0.9)

    kw_j = _jaccard(_kw_set(draft.get("match_keywords", "")),
                    _kw_set(cand_kv.get("match_keywords", "") or cand.get("keywords", "")))

    d_cat, _ = normalize_category(draft.get("category", ""))
    c_cat, _ = normalize_category(cand_kv.get("category", "") or cand.get("category", ""))
    cat_j = _jaccard(_kw_set(d_cat.replace(",", "|")), _kw_set(c_cat.replace(",", "|")))

    ph_j = _jaccard(_kw_set(draft.get("phase", "")),
                    _kw_set(cand_kv.get("phase", "") or cand.get("phase", "")))

    total = (frag_overlap * 0.55 + kw_j * 0.30 + cat_j * 0.10 + ph_j * 0.05)
    return total, {
        "signature_overlap": round(frag_overlap, 2),
        "keyword_jaccard": round(kw_j, 2),
        "category_overlap": round(cat_j, 2),
        "phase_overlap": round(ph_j, 2),
    }


def _verdict(score: float) -> str:
    if score >= _MERGE_TH:
        return "merge-into"
    if score >= _REVIEW_TH:
        return "review-similar"
    return "create"


def review_draft(draft_path: Path, gdir: Path, formal: list[dict], top_n: int = 3) -> dict[str, object]:
    """预审单份草稿，返回报告 dict（不写任何正式库文件）。"""
    draft = _parse_simple_fields(draft_path.read_text(encoding="utf-8", errors="replace"))
    query = " ".join(filter(None, [
        draft.get("match_keywords", ""),
        draft.get("error_signature", ""),
        draft.get("root_cause", "")[:200],
    ]))
    cand_ids = _fts_search(query, formal, top_n=max(top_n, 5))
    results = []
    for cid in cand_ids[:top_n * 2]:
        cand = next((e for e in formal if e["id"] == cid), None)
        if not cand:
            continue
        kv_path = gdir / f"{cid}.kv"
        cand_kv = parse_kv_file(str(kv_path)) if kv_path.exists() else {}
        score, evidence = score_similarity(draft, cand, cand_kv)
        results.append({
            "id": cid,
            "score": round(score, 2),
            "evidence": evidence,
            "root_cause": (cand_kv.get("root_cause", "") or "")[:80],
        })
    results.sort(key=lambda r: -r["score"])
    best = results[0] if results else None
    verdict = _verdict(best["score"]) if best else "create"
    return {
        "draft": draft_path.stem,
        "title": draft.get("title", draft.get("root_cause", ""))[:60],
        "quality": {
            "has_signature": bool(draft.get("error_signature", "").strip()),
            "has_root_cause": len(draft.get("root_cause", "").strip()) > 20,
            "has_rec": bool(draft.get("rec_approach", "").strip()) or bool(draft.get("rec_command", "").strip()),
        },
        "similar": results[:top_n],
        "verdict": verdict,
        "verdict_target": best["id"] if best and verdict != "create" else "",
    }


def cmd_draft_review(
    draft_id: str | None = None,
    *,
    top_n: int = 3,
    as_json: bool = False,
    pdir: str | None = None,
) -> int:
    import json
    project = Path(pdir) if pdir else Path.cwd()
    gdir = project / "knowledge" / "graph"
    drafts_dir = project / "knowledge" / "drafts"
    if not drafts_dir.is_dir():
        log_fail(f"草稿目录不存在: {drafts_dir}")
        return 1

    formal = _load_formal(gdir)
    if not formal:
        log_fail("知识图谱为空，无法预审")
        return 1

    # 草稿两种命名均纳入（DRAFT-*.kv 与 E*-draft-*.kv）
    drafts = sorted(set(drafts_dir.glob("DRAFT-*.kv")) | set(drafts_dir.glob("E*-draft-*.kv")))
    if draft_id:
        m = [d for d in drafts if d.stem == draft_id or d.stem == f"DRAFT-{draft_id}"]
        if not m:
            log_fail(f"草稿不存在: {draft_id}（可用: 前 5 个 {', '.join(d.stem for d in drafts[:5])}...）")
            return 1
        drafts = m

    reports = [review_draft(d, gdir, formal, top_n) for d in drafts]

    # ── 质量门禁预检（空壳草稿单独标记，帮人快速分流）──
    empty = [r for r in reports if not (r["quality"]["has_signature"] and r["quality"]["has_root_cause"])]

    if as_json:
        print(json.dumps({
            "note": "三态建议仅供参考；是否纳入正式知识库由人工审核决定（promote 决策权在人）",
            "total": len(reports),
            "empty_drafts": len(empty),
            "reports": reports,
        }, ensure_ascii=False, indent=2))
        return 0

    # ── 汇总视图 ──
    if not draft_id:
        n_merge = sum(1 for r in reports if r["verdict"] == "merge-into")
        n_review = sum(1 for r in reports if r["verdict"] == "review-similar")
        n_create = sum(1 for r in reports if r["verdict"] == "create")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  📋 草稿预审报告（辅助人工审核，不替代审核决策）           ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"  草稿总数: {len(reports)}  |  空壳(缺 signature/root_cause): {len(empty)}")
        print(f"  预审分布: 疑似重复(merge-into) {n_merge} | 灰区(review-similar) {n_review} | 疑似新知(create) {n_create}")
        print()
        print("  ⚠️ 三态建议仅为相似度计算参考；纳入与否由人工审核决定")
        print()
        # 分组列出（疑似重复优先——最容易合并出价值）
        for group, label in (("merge-into", "🔀 疑似重复（建议人工比对后合并/丢弃）"),
                             ("review-similar", "🔍 灰区（需人工判断关联性）"),
                             ("create", "🆕 疑似新知（无相似条目）")):
            items = [r for r in reports if r["verdict"] == group]
            if not items:
                continue
            print(f"  {label}  [{len(items)}]")
            for r in items[:20]:
                tgt = f" → {r['verdict_target']}" if r["verdict_target"] else ""
                empty_mark = "  ⚠️空壳" if r in empty else ""
                print(f"    {r['draft'][:44]:46s} {r['similar'][0]['score'] if r['similar'] else 0:.2f}{tgt}{empty_mark}")
            if len(items) > 20:
                print(f"    ... 还有 {len(items) - 20} 份")
            print()
        print("  人工纳入命令（决策权在人）:")
        print("    python3 scripts/ohc-run.py graph promote DRAFT-xxx [--target-id Ennn]")
        print("    python3 scripts/ohc-run.py draft-review DRAFT-xxx   # 单份详情比对")
        return 0

    # ── 单份详情视图 ──
    r = reports[0]
    q = r["quality"]
    print(f"── 草稿 {r['draft']} ──")
    print(f"  标题: {r['title']}")
    print(f"  质量预检: signature={'✅' if q['has_signature'] else '❌缺'}  "
          f"root_cause={'✅' if q['has_root_cause'] else '❌缺'}  "
          f"rec={'✅' if q['has_rec'] else '❌缺'}")
    print()
    if r["similar"]:
        print(f"  相似正式条目 TOP{len(r['similar'])}:")
        for s in r["similar"]:
            e = s["evidence"]
            print(f"    {s['id']}  score={s['score']:.2f}  "
                  f"(sig={e['signature_overlap']} kw={e['keyword_jaccard']} cat={e['category_overlap']})")
            print(f"        根因: {s['root_cause']}")
    else:
        print("  无相似正式条目")
    print()
    verdict_cn = {"merge-into": "疑似重复——建议与目标条目人工比对后合并或丢弃",
                  "review-similar": "灰区——需人工判断与目标条目的关联性",
                  "create": "疑似新知——无高相似条目，可考虑人工审核后纳入"}[r["verdict"]]
    print(f"  📌 预审建议: {r['verdict']}"
          + (f" → {r['verdict_target']}" if r["verdict_target"] else ""))
    print(f"     {verdict_cn}")
    print()
    print("  ⚠️ 以上建议仅为相似度计算参考；是否纳入正式知识库由人工审核决定")
    print(f"  人工纳入: python3 scripts/ohc-run.py graph promote {r['draft'].replace('DRAFT-', '')}")
    return 0


def draft_review_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc draft-review",
        description="草稿预审辅助（相似度证据 + 三态建议；纳入决策权在人工审核）",
    )
    parser.add_argument("draft_id", nargs="?", help="草稿名（如 DRAFT-2045；缺省输出全量报告）")
    parser.add_argument("--top", type=int, default=3, help="相似条目 TOP-N（默认 3）")
    parser.add_argument("--json", action="store_true", help="机器可读输出")
    parser.add_argument("--project-dir", "-p", help="项目根目录")
    args = parser.parse_args(argv)
    return cmd_draft_review(
        args.draft_id,
        top_n=args.top,
        as_json=args.json,
        pdir=args.project_dir,
    )
