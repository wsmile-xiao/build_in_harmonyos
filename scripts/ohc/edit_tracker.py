"""Edit tracker — record which source files were modified during compilation.

Solves the fundamental problem: "which files did I actually edit?"
Instead of guessing via exclusion rules, we explicitly track edits.

Lifecycle:
  1. init-build → snapshot() creates baseline fingerprints
  2. AI edits files → track() records each edit (or scan() detects changes)
  3. refresh-patch → get_tracked_files() returns only modified files

Storage: {work_dir}/.edit-tracker.json
  {
    "software": "sed",
    "version": "4.9",
    "baseline": { "relative/path": "sha256", ... },
    "edited": [ "relative/path", ... ],
    "added": [ "relative/path", ... ]
  }
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Optional

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


_TRACKER_FILE = ".edit-tracker.json"

# Dirs/files to skip during baseline scan (build artifacts, not source)
_SKIP_DIRS = {".git", "autom4te.cache", "CMakeFiles", "__pycache__",
              ".libs", ".deps", "build", ".build"}
_SKIP_SUFFIXES = {".o", ".lo", ".la", ".so", ".a", ".pyc", ".gz", ".xz", ".bz2"}


def _tracker_path(work_dir: str | Path) -> Path:
    return Path(work_dir) / _TRACKER_FILE


def _sha256_file(path: Path) -> str:
    """Compute SHA256 of a file."""
    h = sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
    except (OSError, IOError):
        return ""
    return h.hexdigest()


def _is_source_file(path: Path) -> bool:
    """Should this file be included in baseline scan?"""
    if path.name.startswith(".") and path.name != ".gitignore":
        return False
    if path.suffix in _SKIP_SUFFIXES:
        return False
    return True


# ═══════════════════════════════════════════════════════
# snapshot: create baseline fingerprints after extraction
# ═══════════════════════════════════════════════════════

def snapshot(work_dir: str | Path, software: str = "", version: str = "") -> int:
    """Create baseline fingerprint of all source files in work_dir.

    Called by init-build after extraction. Records SHA256 of every
    source file so we can later detect which ones were edited.
    """
    work_dir = Path(work_dir)
    tracker_file = _tracker_path(work_dir)

    if not work_dir.is_dir():
        log_fail(f"源码目录不存在: {work_dir}")
        return 1

    baseline: dict[str, str] = {}
    count = 0
    for f in sorted(work_dir.rglob("*")):
        if not f.is_file():
            continue
        # Skip tracker file itself
        if f.name == _TRACKER_FILE:
            continue
        rel = str(f.relative_to(work_dir))
        # Skip known non-source directories
        parts = Path(rel).parts
        if any(p in _SKIP_DIRS for p in parts):
            continue
        if not _is_source_file(f):
            continue

        h = _sha256_file(f)
        if h:
            baseline[rel] = h
            count += 1

    data = {
        "software": software,
        "version": version,
        "created_at": datetime.now().isoformat(),
        "baseline_file_count": count,
        "baseline": baseline,
        "edited": [],
        "added": [],
    }

    tracker_file.write_text(json.dumps(data, ensure_ascii=False, indent=None),
                            encoding="utf-8")
    log_ok(f"  基线指纹: {count} 个文件 ({work_dir.name})")
    return 0


# ═══════════════════════════════════════════════════════
# track: record a single file edit
# ═══════════════════════════════════════════════════════

def track(work_dir: str | Path, file_path: str) -> int:
    """Record that a file was edited.

    Args:
        work_dir: source tree root
        file_path: relative or absolute path to the edited file
    """
    work_dir = Path(work_dir)
    tracker_file = _tracker_path(work_dir)

    if not tracker_file.exists():
        log_warn("  .edit-tracker.json 不存在，先运行 snapshot")
        return 1

    data = json.loads(tracker_file.read_text(encoding="utf-8"))
    baseline = data.get("baseline", {})

    # Resolve to relative path
    fp = Path(file_path)
    if fp.is_absolute():
        try:
            rel = str(fp.relative_to(work_dir))
        except ValueError:
            log_fail(f"  {file_path} 不在 {work_dir} 下")
            return 1
    else:
        rel = str(fp)

    # Determine: edited (existed in baseline) or added (new file)
    if rel in baseline:
        if rel not in data["edited"]:
            data["edited"].append(rel)
            data["edited"] = sorted(set(data["edited"]))
    else:
        if rel not in data["added"]:
            data["added"].append(rel)
            data["added"] = sorted(set(data["added"]))

    tracker_file.write_text(json.dumps(data, ensure_ascii=False, indent=None),
                            encoding="utf-8")
    return 0


# ═══════════════════════════════════════════════════════
# scan: detect all changes by comparing with baseline
# ═══════════════════════════════════════════════════════

def scan(work_dir: str | Path) -> int:
    """Scan work_dir and detect files whose hash changed since baseline.

    Only detects edited files (hash mismatch). Does NOT auto-scan for
    new files — new files should be recorded via track() explicitly.
    This avoids pulling in build artifacts (Makefile, config.h, etc.)
    as false-positive additions.
    """
    work_dir = Path(work_dir)
    tracker_file = _tracker_path(work_dir)

    if not tracker_file.exists():
        log_fail(f"基线不存在: {tracker_file}")
        return 1

    data = json.loads(tracker_file.read_text(encoding="utf-8"))
    baseline = data.get("baseline", {})

    edited: list[str] = []

    # Check existing files for hash changes only
    for f in sorted(work_dir.rglob("*")):
        if not f.is_file() or f.name == _TRACKER_FILE:
            continue
        rel = str(f.relative_to(work_dir))
        parts = Path(rel).parts
        if any(p in _SKIP_DIRS for p in parts):
            continue

        if rel in baseline:
            current_hash = _sha256_file(f)
            if current_hash and current_hash != baseline[rel]:
                edited.append(rel)

    # Update tracker (only edited; added is managed by track() only)
    data["edited"] = sorted(set(data.get("edited", []) + edited))
    data["scanned_at"] = datetime.now().isoformat()

    tracker_file.write_text(json.dumps(data, ensure_ascii=False, indent=None),
                            encoding="utf-8")

    if edited:
        log_ok(f"  变更文件 ({len(edited)}):")
        for f in edited:
            log_ok(f"    ✏️ {f}")
    else:
        log_info("  无变更")

    return 0


# ═══════════════════════════════════════════════════════
# get_tracked_files: return list for refresh-patch
# ═══════════════════════════════════════════════════════

def get_tracked_files(work_dir: str | Path) -> list[str]:
    """Return all tracked files (edited + added) for patch generation.

    Returns empty list if no tracker exists (caller should fallback).
    """
    work_dir = Path(work_dir)
    tracker_file = _tracker_path(work_dir)

    if not tracker_file.exists():
        return []

    data = json.loads(tracker_file.read_text(encoding="utf-8"))
    edited = data.get("edited", [])
    added = data.get("added", [])
    return sorted(set(edited + added))


def has_tracker(work_dir: str | Path) -> bool:
    """Check if edit tracker exists for this work directory."""
    return _tracker_path(work_dir).exists()


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

def edit_tracker_cli(argv: list[str] | None = None) -> int:
    """CLI: python3 ohc-run.py track-edit [action] [args]"""
    import argparse

    parser = argparse.ArgumentParser(prog="ohc track-edit",
        description="追踪源码编辑记录")
    sub = parser.add_subparsers(dest="action")

    p_scan = sub.add_parser("scan", help="扫描变更（比对基线指纹）")
    p_scan.add_argument("software")
    p_scan.add_argument("version")
    p_scan.add_argument("--project-dir")

    p_track = sub.add_parser("add", help="记录单个文件编辑")
    p_track.add_argument("software")
    p_track.add_argument("version")
    p_track.add_argument("file", help="被编辑的文件（相对路径）")
    p_track.add_argument("--project-dir")

    p_list = sub.add_parser("list", help="列出所有追踪到的变更")
    p_list.add_argument("software")
    p_list.add_argument("version")
    p_list.add_argument("--project-dir")

    args = parser.parse_args(argv)
    pdir = getattr(args, "project_dir", None)
    project = Path(pdir) if pdir else Path(find_project_dir())

    if not args.action:
        parser.print_help()
        return 1

    # Resolve work_dir from build context
    ctx_files = sorted(project.glob(f".build-context-{args.software}-{args.version}*"))
    if not ctx_files:
        log_fail(f"找不到 .build-context-{args.software}-{args.version}")
        return 1

    ctx = ctx_files[0].read_text(encoding="utf-8")
    work_dir = ""
    for line in ctx.split("\n"):
        m = line.strip().split("=", 1)
        if len(m) == 2 and m[0] == "export BUILD_SRC_DIR":
            work_dir = m[1].strip('"').strip("'")
            break

    if not work_dir or not Path(work_dir).exists():
        log_fail(f"源码目录不存在: {work_dir}")
        return 1

    if args.action == "scan":
        return scan(work_dir)
    elif args.action == "add":
        return track(work_dir, args.file)
    elif args.action == "list":
        files = get_tracked_files(work_dir)
        if not files:
            log_info("无追踪到的变更")
        else:
            print(f"\n  📝 Tracked edits ({len(files)} files):\n")
            for f in files:
                print(f"    {f}")
            print()
        return 0

    return 1
