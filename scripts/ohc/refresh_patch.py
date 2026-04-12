"""Refresh patches — generate per-file diff patches.
"""
from __future__ import annotations
import difflib
import filecmp
import hashlib
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail

EXCLUDE_DIRS = {"build", ".git", "autom4te.cache", "CMakeFiles",
                "__pycache__", ".libs", ".deps"}
EXCLUDE_SUFFIXES = (".o", ".lo", ".la", ".so", ".a")
EXCLUDE_FILES = {"config.status", "config.log"}

_CONTEXT_LINES = 10  # unified diff context lines


def _should_ignore(rel_path: Path) -> bool:
    """Check if a relative path should be excluded from diff."""
    parts = rel_path.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    if rel_path.suffix in EXCLUDE_SUFFIXES:
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    return False


def _diff_files(orig: Path, mod: Path) -> str | None:
    """Generate unified diff between two files using difflib.
    Returns diff string or None if identical."""
    try:
        orig_lines = orig.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        mod_lines = mod.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except Exception:
        # Binary file fallback: compare bytes
        if orig.read_bytes() == mod.read_bytes():
            return None
        return f"Binary files differ\n"

    if orig_lines == mod_lines:
        return None

    diff = difflib.unified_diff(
        orig_lines, mod_lines,
        fromfile=str(orig), tofile=str(mod),
        n=_CONTEXT_LINES,
    )
    result = "".join(diff)
    return result if result else None


def _find_differences(orig_dir: Path, mod_dir: Path) -> list[tuple[Path, Path]]:
    """Recursively find all differing files using filecmp + difflib.
    Returns list of (orig_file, mod_file) pairs."""
    diffs: list[tuple[Path, Path]] = []

    def _compare(dcmp: filecmp.dircmp, rel: Path) -> None:
        # Files only in mod (new files)
        for f in dcmp.right_only:
            rp = rel / f
            if _should_ignore(rp):
                continue
            mod_file = dcmp.right / f
            if mod_file.is_file():
                diffs.append((None, mod_file))

        # Files that differ
        for f in dcmp.diff_files:
            rp = rel / f
            if _should_ignore(rp):
                continue
            diffs.append((dcmp.left / f, dcmp.right / f))

        # Files only in orig (deleted files) — skip for patches

        # Recurse into subdirectories
        for sub, sub_dcmp in dcmp.subdirs.items():
            rp = rel / sub
            if sub in EXCLUDE_DIRS:
                continue
            _compare(sub_dcmp, rp)

    dcmp = filecmp.dircmp(orig_dir, mod_dir)
    _compare(dcmp, Path("."))
    return diffs


def _validate_patch_format(patch_file: Path) -> tuple[int, list[str]]:
    """Validate patch format. Returns (status, warnings).
    0=ok, 1=warning(fixed), 2=error"""
    if not patch_file.exists() or patch_file.stat().st_size < 10:
        return 2, ["E058-4: empty or missing"]

    content = patch_file.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    warnings = []

    diff_count = sum(1 for l in lines if l.startswith("diff "))
    if diff_count > 1:
        return 2, ["E058-1: multiple diff headers — manual fix needed"]

    has_abs = any(l.startswith("--- /") for l in lines)
    if has_abs:
        warnings.append("E058-2: absolute paths (warning)")

    # E058-3: missing diff header but has --- +++
    has_header = any(l.startswith("---") for l in lines)
    has_plus = any(l.startswith("+++") for l in lines)
    if diff_count == 0 and has_header and has_plus:
        first_minus = next(i for i, l in enumerate(lines) if l.startswith("--- "))
        first_plus = next(i for i, l in enumerate(lines) if l.startswith("+++ "))
        orig_path = lines[first_minus][4:].split("\t")[0]
        mod_path = lines[first_plus][4:].split("\t")[0]
        header = f"diff -ruN {orig_path} {mod_path}\n"
        patch_file.write_text(header + content, encoding="utf-8")
        warnings.append("E058-3: missing diff header (auto-fixed)")
        return 1, warnings

    if diff_count == 0 and not has_header:
        return 2, ["E058-4: no diff content"]

    return (1 if warnings else 0), warnings


def _patch_stats(patch_file: Path) -> dict:
    content = patch_file.read_text(encoding="utf-8", errors="replace")
    files = len(re.findall(r'^diff ', content, re.M))
    added = len(re.findall(r'^\+', content, re.M)) - len(re.findall(r'^\+\+\+', content, re.M))
    removed = len(re.findall(r'^-', content, re.M)) - len(re.findall(r'^---', content, re.M))
    return {"files": files, "added": max(0, added), "removed": max(0, removed)}


def _dry_run(patch_file: Path, orig_dir: Path) -> bool:
    """Verify patch with dry-run (requires external patch command)."""
    try:
        r = subprocess.run(
            ["patch", "--dry-run", "-p1"],
            stdin=open(patch_file), cwd=str(orig_dir),
            capture_output=True, timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def _compute_hash(directory: Path) -> str:
    """Aggregate hash of all files in directory."""
    h = hashlib.sha256()
    for f in sorted(directory.rglob("*")):
        if f.is_file() and not any(p in EXCLUDE_DIRS for p in f.relative_to(directory).parts):
            if f.suffix not in EXCLUDE_SUFFIXES and f.name not in EXCLUDE_FILES:
                h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _locate_dirs(software: str, version: str, project: Path) -> tuple[Path, Path, Path]:
    """Locate orig dir, work dir, patch dir."""
    letter = software[0].lower()
    ver_dir = project / "archives" / letter / software / version
    patch_dir = ver_dir / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)

    # Load build context
    ctx_files = list(project.glob(f".build-context-{software}-{version}*"))
    ctx_vars: dict[str, str] = {}
    if ctx_files:
        for line in ctx_files[0].read_text(encoding="utf-8", errors="replace").split("\n"):
            m = re.match(r'^(?:export\s+)?(\w+)=(.*)', line.strip())
            if m:
                ctx_vars[m.group(1)] = m.group(2).strip().strip('"').strip("'")

    # Locate orig dir
    orig_dir = None
    if "BUILD_SRC_ORIG_DIR" in ctx_vars:
        p = Path(ctx_vars["BUILD_SRC_ORIG_DIR"])
        if p.exists():
            orig_dir = p
    if not orig_dir:
        src_dir = ctx_vars.get("BUILD_SRC_DIR", "")
        if src_dir:
            p = Path(src_dir).parent / f"{Path(src_dir).name}.orig"
            if p.exists():
                orig_dir = p
            else:
                p = Path(src_dir + ".orig")
                if p.exists():
                    orig_dir = p

    # Locate work dir
    work_dir = None
    if "BUILD_SRC_DIR" in ctx_vars:
        p = Path(ctx_vars["BUILD_SRC_DIR"])
        if p.exists():
            work_dir = p

    if not orig_dir or not work_dir:
        log_fail(f"无法定位源码目录: orig={orig_dir}, work={work_dir}")
        return Path(), Path(), patch_dir

    if orig_dir.resolve() == work_dir.resolve():
        log_fail("orig 和 work 目录相同")
        return Path(), Path(), patch_dir

    return orig_dir, work_dir, patch_dir


def auto_mode(software: str, version: str, pdir: str | None = None) -> int:
    project = Path(pdir) if pdir else Path(find_project_dir())
    log_info(f"refresh-patch --auto {software} {version}")

    orig_dir, work_dir, patch_dir = _locate_dirs(software, version, project)
    if not orig_dir.exists():
        log_fail(f"orig 目录不存在: {orig_dir}")
        return 2

    # Create staging dir
    staging = patch_dir / ".patch-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    # Find differences using filecmp (replaces diff -rq)
    log_info("  扫描差异文件...")
    diff_pairs = _find_differences(orig_dir, work_dir)

    if not diff_pairs:
        log_ok("  无差异，保留现有补丁")
        shutil.rmtree(staging)
        return 0

    # Generate per-file patches using difflib
    patch_num = 1
    for orig_file, mod_file in diff_pairs:
        rel_path = mod_file.relative_to(work_dir) if mod_file.is_relative_to(work_dir) else mod_file.name
        patch_name = f"{patch_num:04d}-{str(rel_path).replace('/', '-')}.patch"
        patch_file = staging / patch_name

        if orig_file is None:
            # New file only — generate diff from /dev/null
            try:
                mod_lines = mod_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            except Exception:
                continue
            rel = f"b/{rel_path}"
            diff_text = "".join(difflib.unified_diff([], mod_lines, fromfile="/dev/null", tofile=rel, n=_CONTEXT_LINES))
            if not diff_text:
                continue
        else:
            diff_text = _diff_files(orig_file, mod_file)
            if diff_text is None:
                continue

        # Replace paths: orig_dir → a/, work_dir → b/
        diff_text = diff_text.replace(str(orig_dir) + "/", "a/")
        diff_text = diff_text.replace(str(work_dir) + "/", "b/")
        patch_file.write_text(diff_text, encoding="utf-8")

        # Validate + auto-fix
        status, warns = _validate_patch_format(patch_file)
        if status == 2:
            log_warn(f"  ⚠️ {patch_name}: {warns}")
            patch_file.unlink()
            continue

        # Dry run
        if not _dry_run(patch_file, orig_dir):
            log_warn(f"  ⚠️ {patch_name}: dry-run 失败")
            patch_file.unlink()
            continue

        stats = _patch_stats(patch_file)
        log_ok(f"  ✅ {patch_name} ({stats['files']} files, +{stats['added']}/-{stats['removed']})")
        patch_num += 1

    # Atomic replace
    new_patches = list(staging.glob("*.patch"))
    if not new_patches:
        log_info("  无有效新补丁，保留现有")
        shutil.rmtree(staging)
        return 0

    # Backup old patches
    old_patches = list(patch_dir.glob("*.patch"))
    if old_patches:
        backup = patch_dir / f".patch-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        backup.mkdir()
        for p in old_patches:
            shutil.move(str(p), backup / p.name)

    # Move new patches
    for p in new_patches:
        shutil.move(str(p), patch_dir / p.name)
    shutil.rmtree(staging)

    # Hash binding
    orig_hash = _compute_hash(orig_dir)
    work_hash = _compute_hash(work_dir)
    log_info(f"  orig hash: {orig_hash}")
    log_info(f"  work hash: {work_hash}")

    # Update manifest
    letter = software[0].lower()
    manifest = project / "archives" / letter / software / version / "manifest.yaml"
    if manifest.exists():
        gen_info = (
            f"\npatch_generation:\n"
            f"  method: per-file-difflib\n"
            f"  source_orig_dir: {orig_dir}\n"
            f"  source_work_dir: {work_dir}\n"
            f"  source_orig_hash: {orig_hash}\n"
            f"  source_work_hash: {work_hash}\n"
            f"  generated_at: '{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}'\n"
            f"  patches_count: {len(new_patches)}\n"
        )
        content = manifest.read_text(encoding="utf-8")
        content = re.sub(r'\npatch_generation:.*', '', content, flags=re.DOTALL)
        manifest.write_text(content + gen_info, encoding="utf-8")

    log_ok(f"✅ 生成 {len(new_patches)} 个补丁")
    return 0


def refresh_patch_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc refresh-patch")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--all", action="store_true", dest="all_mode")
    parser.add_argument("args", nargs="*")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    pdir = getattr(args, "project_dir", None)

    if args.auto and len(args.args) >= 2:
        return auto_mode(args.args[0], args.args[1], pdir)
    else:
        parser.print_help()
        return 1
