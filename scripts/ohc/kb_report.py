"""kb_report — 知识库质量月报（纯本地，社区模式，v12.6 L6）

设计原则（用户约束）: 不依赖 CI。每个贡献者在自己机器上跑，
聚合的是**本地数据**（graph metrics / prescan hit_count / 本地构建日志）；
跨人汇聚靠 git（metrics 已随 .kv 与规则文件进库，pull/merge 自然合并）。

内容:
  1. 知识活跃度: metrics_last_used 分布（活跃/陈旧/从未命中）
  2. 预扫描价值: prescan 规则 hit_count top（指导规则投资/淘汰）
  3. 未命中采购清单: --scan-logs 扫本地构建日志中 engine 未匹配的错误
     （这是知识库该补什么的直接信号）

用法:
  ohc-run.py kb-report
  ohc-run.py kb-report --scan-logs <dir|glob>    # 含未命中分析
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn

_STALE_DAYS = 180
_ERROR_LINE_RE = re.compile(
    r"(ld\.lld: error:|ld: error:|error:|fatal error:|undefined reference|"
    r"No rule to make target|cannot find -l|configure: error|CMake Error)",
    re.I,
)


def _load_sidecar_metrics(pdir: Path) -> dict:
    """v12.6.1: 本地 sidecar 命中记录（engine 写入，gitignored）。

    v12.20 返回归一化 v2 结构 {"entries": {eid: {...}}, "pending": [...]}；
    兼容 v1 顶层 {eid: "date"}。
    """
    import json
    sc = pdir / "knowledge" / ".metrics-local.json"
    if not sc.exists():
        return {}
    try:
        data = json.loads(sc.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(data.get("entries"), dict):
        return data
    # v1 → v2 归一
    entries = {k: {"last": v} for k, v in data.items()
               if k not in ("entries", "pending") and isinstance(v, str)}
    return {"entries": entries, "pending": []}


def _parse_kv_metrics(gdir: Path, sidecar: dict | None = None) -> list[dict]:
    rows = []
    sc_entries = (sidecar or {}).get("entries", {})
    for kvf in sorted(gdir.glob("E*.kv")):
        fields = {}
        for line in kvf.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"^(\w+):\s*(.*)$", line)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2).strip()
        eid = fields.get("id", kvf.stem)
        # sidecar（当前机制）优先，.kv 遗留字段兜底
        sc_ent = sc_entries.get(eid) or {}
        rows.append({
            "id": eid,
            "last_used": sc_ent.get("last", "")
            if isinstance(sc_ent, dict) else sc_ent,
            "confidence": fields.get("metrics_confidence", ""),
            "hits_success": sc_ent.get("s", 0)
            if isinstance(sc_ent, dict) else 0,
            "hits_fail": sc_ent.get("f", 0)
            if isinstance(sc_ent, dict) else 0,
        })
    return rows


def _parse_prescan_hits(pdir: Path) -> list[dict]:
    rp = pdir / "knowledge" / "graph" / "pre-scan-rules.yaml"
    if not rp.exists():
        return []
    rules, cur = [], None
    for line in rp.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("- id:"):
            cur = {"id": s.split(":", 1)[1].strip(), "hit": 0, "desc": ""}
            rules.append(cur)
        elif cur is not None:
            m = re.match(r"hit_count:\s*(\d+)", s)
            if m:
                cur["hit"] = int(m.group(1))
            m2 = re.match(r'description:\s*"?(.+?)"?$', s)
            if m2 and not cur["desc"]:
                cur["desc"] = m2.group(1)[:60]
    return rules


def _collect_error_lines(paths: list[Path]) -> list[str]:
    seen, errors = set(), []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            if _ERROR_LINE_RE.search(line):
                key = re.sub(r"0x[0-9a-f]+|\d+", "N", line.strip())[:140]
                if key not in seen:
                    seen.add(key)
                    errors.append(line.strip()[:200])
    return errors


def kb_report_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc kb-report",
        description="知识库质量月报（本地数据聚合，社区 git 同步汇聚）",
    )
    parser.add_argument("--scan-logs", "-l", help="构建日志文件/glob（如 'archives/*/*/*/.build-*.log'），含未命中分析")
    parser.add_argument("--project-dir", "-p")
    args = parser.parse_args(argv)

    pdir = Path(find_project_dir())
    gdir = pdir / "knowledge" / "graph"
    today = date.today()

    # ── 1. 知识活跃度 ──
    rows = _parse_kv_metrics(gdir, _load_sidecar_metrics(pdir))
    total = len(rows)
    active = stale = never = 0
    stale_ids = []
    for r in rows:
        lu = r["last_used"]
        if not lu:
            never += 1
        else:
            try:
                d = datetime.strptime(lu[:10], "%Y-%m-%d").date()
                age = (today - d).days
                if age > _STALE_DAYS:
                    stale += 1
                    stale_ids.append(f"{r['id']}({age}d)")
                else:
                    active += 1
            except ValueError:
                never += 1

    print("╔══════════════════════════════════════════════════════════╗")
    print("║  📊 知识库质量月报（本地聚合，git 同步社区汇聚）           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  知识条目: {total} | 活跃(180d内命中): {active} | 陈旧: {stale} | 从未命中: {never}")
    if stale_ids:
        print(f"  陈旧 TOP: {', '.join(stale_ids[:10])}{' ...' if len(stale_ids) > 10 else ''}")
        print("  （陈旧条目候选：复核是否已过时/可归档）")

    # ── 2. 预扫描价值 ──
    rules = _parse_prescan_hits(pdir)
    hit_rules = [r for r in rules if r["hit"] > 0]
    if hit_rules:
        hit_rules.sort(key=lambda r: -r["hit"])
        print(f"\n  预扫描规则命中 TOP（{len(hit_rules)}/{len(rules)} 条规则有命中）:")
        for r in hit_rules[:10]:
            print(f"    {r['hit']:4d}  {r['id']}: {r['desc']}")
    else:
        print(f"\n  预扫描: {len(rules)} 条规则暂无命中记录（回填机制 v12.5 起，积累中）")

    # ── 3. 未命中采购清单 ──
    if args.scan_logs:
        import glob as _glob
        log_paths = []
        for pat in args.scan_logs.split():
            log_paths.extend(Path(x) for x in _glob.glob(pat))
        log_paths = [p for p in log_paths if p.is_file()][:200]
        if not log_paths:
            log_warn(f"未找到日志: {args.scan_logs}")
            return 0
        errors = _collect_error_lines(log_paths)
        if not errors:
            print(f"\n  日志扫描: {len(log_paths)} 个文件，无未处理错误行 ✅")
            return 0

        from .engine import run_engine
        misses = []
        for err in errors[:120]:
            result = run_engine(err)
            if not result.matched:
                misses.append(err)
        print(f"\n  日志扫描: {len(log_paths)} 文件 | 错误行 {len(errors)} | 未命中 {len(misses)}")
        if misses:
            print("  📋 知识采购清单（未命中错误，建议 graph add 草稿化→人工审核纳入）:")
            for m in misses[:10]:
                print(f"    - {m[:120]}")
            print(f"    {'... 还有 ' + str(len(misses) - 10) + ' 条' if len(misses) > 10 else ''}")
        else:
            print("  ✅ 全部错误行都有知识命中")
    print()
    return 0
