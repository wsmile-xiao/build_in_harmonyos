"""Finalize compilation archive — cleanup, validation.
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


def _sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._+-]', '', s)


def _parse_manifest(path: Path) -> dict:
    """Simple YAML key-value parser for manifest.yaml."""
    data: dict[str, str | list[str]] = {}
    if not path.exists():
        return data
    current_list_key = None
    for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if line.startswith(" ") or line.startswith("\t"):
            stripped = line.strip()
            if stripped.startswith("- ") and current_list_key:
                data.setdefault(current_list_key, [])
                data[current_list_key].append(stripped[2:].strip())
            continue
        current_list_key = None
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            val = val.strip().strip('"').strip("'")
            if val:
                data[key.strip()] = val
            elif val == "" or not val:
                current_list_key = key.strip()
    return data


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def finalize_archive(software: str, version: str, pdir: str | None = None) -> int:
    project = Path(pdir) if pdir else Path(find_project_dir())
    software = _sanitize(software)
    version = _sanitize(version)
    letter = software[0].lower()
    sw_dir = project / "archives" / letter / software
    ver_dir = sw_dir / version

    if not ver_dir.exists():
        log_fail(f"版本目录不存在: {ver_dir}")
        return 1

    manifest = ver_dir / "manifest.yaml"
    mf = _parse_manifest(manifest)
    status = str(mf.get("status", "unknown"))

    log_info(f"finalize-archive: {software} {version} (status={status})")

    # Phase 1: Cleanup temp files
    log_info("  Phase 1: 清理临时文件...")
    for subdir in ["", "patches", "reports", "scripts", "logs", "packaging"]:
        d = ver_dir / subdir if subdir else ver_dir
        for pat in ["*.tmp", "*.bak"]:
            for f in d.glob(pat):
                f.unlink()
    # Clean packaging/debug/ non-debug files
    debug_dir = ver_dir / "packaging" / "debug"
    if debug_dir.exists():
        for f in debug_dir.iterdir():
            if f.suffix != ".debug":
                f.unlink()

    # Phase 2: Required files check
    log_info("  Phase 2: 必填文件校验...")
    missing = 0

    # Software level: README.md + manifest.yaml
    for f in ["README.md"]:
        p = sw_dir / f
        if not p.exists() or len(p.read_text(encoding="utf-8", errors="replace").splitlines()) < 5:
            log_warn(f"  ⚠️ 软件级缺失: {f}")
            missing += 1

    # Version level files (notes.md)
    notes_path = ver_dir / "notes.md"
    notes_ok = False
    if notes_path.exists() and len(notes_path.read_text(encoding="utf-8", errors="replace").splitlines()) >= 5:
        notes_ok = True
    if not notes_ok:
        log_warn("  ⚠️ 版本级缺失: notes.md")
        missing += 1

    for f in ["manifest.yaml"]:
        p = ver_dir / f
        if not p.exists() or len(p.read_text(encoding="utf-8", errors="replace").splitlines()) < 5:
            log_warn(f"  ⚠️ 版本级缺失: {f}")
            missing += 1

    # Version level dirs
    for d in ["patches", "reports", "packaging"]:
        if not (ver_dir / d).is_dir():
            log_warn(f"  ⚠️ 目录缺失: {d}")
            missing += 1

    # Packaging deliverables (only for published/built)
    if status in ("published", "built"):
        rel_tars = list((ver_dir / "packaging").glob("*-ohos-aarch64.tar.gz"))
        debug_tars = list((ver_dir / "packaging").glob("*-debug.tar.gz"))
        if not rel_tars:
            log_warn("  ⚠️ 缺少 release tar.gz")
            missing += 1
        if not debug_tars:
            log_warn("  ⚠️ 缺少 debug tar.gz")

    # Phase 3: Consistency check
    log_info("  Phase 3: 一致性检查...")
    issues = 0

    # Status consistency (notes.md)
    progress = ver_dir / "notes.md"
    if progress.exists():
        pc = progress.read_text(encoding="utf-8", errors="replace")
        progress_status = "unknown"
        for m in re.finditer(r'(?:状态|status)[：:]\s*(.+)', pc, re.I):
            progress_status = m.group(1).strip()
        if progress_status != "unknown" and status not in progress_status:
            log_warn(f"  ⚠️ 状态不一致: notes={progress_status} vs manifest={status}")
            issues += 1
        if "### 对话 #" not in pc:
            log_warn("  ⚠️ notes.md 无对话记录")
            issues += 1

    # Patch count consistency
    mf_patches = str(mf.get("patches_applied", ""))
    if mf_patches:
        mf_count = len([x for x in mf_patches.strip("[]").split(",") if x.strip()])
        disk_count = len(list((ver_dir / "patches").glob("000*.patch")))
        if mf_count != disk_count:
            log_warn(f"  ⚠️ 补丁数不一致: manifest={mf_count} vs disk={disk_count}")
            issues += 1

    # Phase 4: Report
    patches = sorted((ver_dir / "patches").glob("000*.patch"))
    reports = len(list((ver_dir / "reports").glob("*.md")))
    pkg_count = len(list((ver_dir / "packaging").glob("*.tar.gz")))

    print(f"\n  📊 归档报告:")
    print(f"     软件:     {software} {version}")
    print(f"     状态:     {status}")
    print(f"     补丁:     {len(patches)} 个")
    print(f"     报告:     {reports} 个")
    print(f"     打包产物: {pkg_count} 个")
    print(f"     一致性问题: {issues}")
    print(f"     缺失项:   {missing}")

    if missing > 0 or issues > 0:
        log_warn(f"⚠️ finalize 完成，有 {missing} 个缺失 + {issues} 个一致性问题")
        return 2

    log_ok("✅ finalize-archive 通过")
    return 0


def finalize_archive_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc finalize-archive")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    return finalize_archive(args.software, args.version,
                             getattr(args, "project_dir", None))
