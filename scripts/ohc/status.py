"""Build status scanner — find in-progress builds across sessions.

Usage:
    python3 -m ohc status              # Show all builds
    python3 -m ohc status --paused     # Show only paused/failed builds
    python3 -m ohc status --json       # Machine-readable output
"""
from __future__ import annotations

import glob
import json
import os
import sys
from typing import Optional

from .models import parse_build_context
from .utils import find_project_dir, graph_dir


def _load_build_status(project_dir: str) -> dict:
    """Load .build-status.json."""
    path = os.path.join(project_dir, ".build-status.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _scan_context_files(project_dir: str) -> list[dict]:
    """Scan for .build-context-* files as fallback data source."""
    pattern = os.path.join(project_dir, ".build-context-*")
    results = []
    for path in glob.glob(pattern):
        try:
            ctx = parse_build_context(path)
            results.append({
                "file": os.path.basename(path),
                "software": ctx.get("BUILD_SOFTWARE", ""),
                "version": ctx.get("BUILD_VERSION", ""),
                "archive_dir": ctx.get("BUILD_ARCHIVE_DIR", ""),
                "src_dir": ctx.get("BUILD_SRC_DIR", ""),
                "build_system": ctx.get("BUILD_SYSTEM", ""),
            })
        except Exception:
            continue
    return results


def scan_builds(project_dir: str | None = None) -> list[dict]:
    """Scan for all known builds and their status.

    Combines:
    1. .build-status.json (authoritative, from handoff.py)
    2. .build-context-* files (fallback discovery)
    """
    pdir = project_dir or find_project_dir()
    status = _load_build_status(pdir)
    context_files = _scan_context_files(pdir)

    # Start with build-status entries
    builds = {}
    for key, info in status.items():
        builds[key] = {
            **info,
            "source": "build-status",
        }

    # Merge context files (for builds started but never failed/handed-off)
    for ctx in context_files:
        key = f"{ctx['software']}/{ctx['version']}"
        if key not in builds:
            builds[key] = {
                "software": ctx["software"],
                "version": ctx["version"],
                "status": "initialized",
                "archive_dir": ctx["archive_dir"],
                "src_dir": ctx["src_dir"],
                "build_system": ctx.get("build_system", ""),
                "source": "build-context",
            }

    return list(builds.values())


def format_status(builds: list[dict]) -> str:
    """Format build status for human-readable output."""
    if not builds:
        return "📭 没有进行中的编译。\n"

    lines = ["", "📊 编译状态一览:", ""]

    for b in sorted(builds, key=lambda x: x.get("timestamp", "")):
        sw = b.get("software", "?")
        ver = b.get("version", "?")
        status = b.get("status", "unknown")
        step = b.get("step_failed", "")
        hit = b.get("knowledge_hit", "")
        gap = b.get("knowledge_gap", False)
        resume = b.get("resume_cmd", "")

        # Status emoji
        if status == "completed":
            icon = "✅"
        elif status == "success":
            icon = "✅"
        elif status == "paused":
            icon = "🔄"
        elif status == "failed":
            icon = "❌"
        elif status == "running":
            icon = "🏃"
        elif status == "initialized":
            icon = "📦"
        else:
            icon = "❓"

        line = f"  {icon} {sw} {ver}: {status}"
        if step:
            line += f" (停在 {step})"
        if hit and hit != "none":
            line += f" [命中 {hit}]"
        if gap:
            line += " [⚠️ 知识缺口]"
        lines.append(line)

        if resume:
            lines.append(f"     → 恢复: {resume}")

        # Show handoff.json path for paused/failed builds
        archive_dir = b.get("archive_dir", "")
        if archive_dir and status in ("paused", "failed"):
            hj = os.path.join(archive_dir, ".handoff.json")
            if os.path.isfile(hj):
                lines.append(f"     📄 HANDOFF: {hj}")

    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# CLI entry
# ═══════════════════════════════════════════════════════

def status_cli(argv: list[str] | None = None) -> int:
    """CLI for: python3 -m ohc status"""
    import argparse
    parser = argparse.ArgumentParser(prog="ohc status", description="Show build status")
    parser.add_argument("--paused", action="store_true", help="Show only paused/failed builds")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--project-dir", help="Project root directory")

    args = parser.parse_args(argv)

    pdir = args.project_dir or find_project_dir()
    builds = scan_builds(pdir)

    if args.paused:
        builds = [b for b in builds if b.get("status") in ("paused", "failed")]

    if args.json:
        print(json.dumps(builds, ensure_ascii=False, indent=2))
    else:
        print(format_status(builds), end="")

    return 0
