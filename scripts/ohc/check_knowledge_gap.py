"""Check knowledge completeness in compilation archive.
"""
from __future__ import annotations
import re
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


def check_knowledge_gap(name: str, version: str, pdir: str | None = None) -> int:
    project = Path(pdir) if pdir else Path(find_project_dir())
    letter = name[0].lower()
    ver_dir = project / "archives" / letter / name / version

    if not ver_dir.exists():
        log_fail(f"档案不存在: {ver_dir}")
        return 2

    # Scan PROGRESS.md
    progress = ver_dir / "PROGRESS.md"
    extracted = pending = failed = 0
    pending_items: list[str] = []

    if progress.exists():
        in_section = False
        for line in progress.read_text(encoding="utf-8").split("\n"):
            # Detect knowledge section
            if re.search(r'(发现与知识|知识积累|discoveries|findings)', line, re.I):
                in_section = True
                continue
            if in_section and (line.startswith("## ") or line.strip() == "---"):
                in_section = False
                continue
            if not in_section:
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith("<!--") or stripped.startswith("#"):
                continue

            if "✅" in stripped:
                extracted += 1
            elif re.search(r'(⏳|TODO|待评估|待提取|FIXME)', stripped, re.I):
                pending += 1
                pending_items.append(stripped)
            elif "❌" in stripped:
                failed += 1
            elif stripped.startswith("- ") or stripped.startswith("* "):
                pending += 1
                pending_items.append(stripped)

    # Check manifest.yaml knowledge_gained
    manifest = ver_dir / "manifest.yaml"
    unreferenced = 0
    knowledge_count = 0
    if manifest.exists():
        in_kg = False
        for line in manifest.read_text(encoding="utf-8").split("\n"):
            if line.strip().startswith("knowledge_gained:"):
                in_kg = True
                continue
            if in_kg:
                if line.strip().startswith("- "):
                    knowledge_count += 1
                    if not re.search(r'(knowledge_ref|ref:|reference:)', line, re.I):
                        unreferenced += 1
                elif not line.startswith(" ") and not line.startswith("\t"):
                    in_kg = False

    # Report
    total = extracted + pending + failed
    log_info(f"PROGRESS.md: total={total} extracted={extracted} pending={pending} failed={failed}")
    log_info(f"manifest.yaml: knowledge_count={knowledge_count} unreferenced={unreferenced}")

    if pending_items:
        log_warn("待处理条目:")
        for item in pending_items[:10]:
            log_warn(f"  {item[:80]}")

    has_gap = pending > 0 or failed > 0 or unreferenced > 0
    if has_gap:
        log_warn(f"⚠️ 存在知识遗漏: pending={pending} failed={failed} unreferenced={unreferenced}")
        # Remove stale marker if exists
        marker = ver_dir / ".knowledge-done"
        marker.unlink(missing_ok=True)
        return 3

    # Write completion marker (finish.py checks this as a gate)
    marker = ver_dir / ".knowledge-done"
    marker.write_text(
        f"checked_at={__import__('datetime').datetime.now().isoformat()}\n"
        f"pending={pending}\nfailed={failed}\nunreferenced={unreferenced}\n",
        encoding="utf-8",
    )
    log_ok("✅ 知识完整性检查通过")
    return 0


def check_knowledge_gap_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc check-knowledge-gap")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    return check_knowledge_gap(args.software, args.version,
                                getattr(args, "project_dir", None))
