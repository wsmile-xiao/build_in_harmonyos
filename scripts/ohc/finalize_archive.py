"""Finalize compilation archive — cleanup, RELEASENOTE, validation.
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

    # Phase 2: Generate software-level RELEASENOTE.md
    log_info("  Phase 2: 生成 RELEASENOTE.md...")
    rn = sw_dir / "RELEASENOTE.md"

    build_system = str(mf.get("build_system", "unknown"))
    source_url = str(mf.get("source_url", ""))
    binary_count = str(mf.get("binary_count", "N/A"))
    exclude_list = mf.get("exclude_list", [])
    if isinstance(exclude_list, str):
        exclude_list = [exclude_list]

    # Quality report
    quality = "N/A"
    qr = ver_dir / "reports" / "quality-report.md"
    if qr.exists():
        content = qr.read_text(encoding="utf-8", errors="replace")
        if "PASS" in content and "FAIL" not in content:
            quality = "PASS"
        elif "FAIL" in content:
            quality = "FAIL-WARN"

    # Patches
    patches = sorted((ver_dir / "patches").glob("000*.patch"))
    patch_names = [p.name for p in patches]

    # Package info
    tars = list((ver_dir / "packaging").glob("*-ohos-aarch64*.tar.gz"))
    pkg_size = _human_size(sum(t.stat().st_size for t in tars)) if tars else "N/A"
    pkg_names = [t.name for t in tars]

    # Binary names
    bins = list((ver_dir / "packaging" / "bin").glob("*")) if (ver_dir / "packaging" / "bin").exists() else []
    bin_names = [b.name for b in bins[:5]]

    # Version list
    versions = sorted([d.name for d in sw_dir.iterdir() if d.is_dir() and d.name[0].isdigit()], reverse=True)

    # Build RELEASENOTE
    lines = [
        f"# {software} — HarmonyOS aarch64 预编译包\n",
        f"## 快速安装\n",
        f"```bash\ntar xzf {software}-{version}-ohos-aarch64.tar.gz -C ~/usr/local\n",
        f"cd {software}-{version}-ohos-aarch64 && sh install-{software}-{version}.sh\n```\n",
        f"## 可用版本\n",
        f"| 版本 | 状态 | 补丁数 |",
        f"|------|------|--------|",
    ]
    for v in versions:
        vm = sw_dir / v / "manifest.yaml"
        vmf = _parse_manifest(vm)
        vs = str(vmf.get("status", "unknown"))
        vp = len(list((sw_dir / v / "patches").glob("000*.patch")))
        lines.append(f"| {v} | {vs} | {vp} |")

    lines.extend([
        f"\n## 当前版本 ({version}) 详情\n",
        f"### 包内容",
        f"- 二进制: {binary_count}",
        f"- 包大小: {pkg_size}",
    ])
    if bin_names:
        lines.append(f"- 命令: {', '.join(bin_names)}")

    if exclude_list:
        lines.extend([
            f"\n### 排除命令",
            f"- {', '.join(str(e) for e in exclude_list[:10])}",
        ])

    lines.extend([
        f"\n### 编译信息",
        f"- 构建系统: {build_system}",
        f"- 目标: ohos-aarch64",
        f"- 质量门禁: {quality}",
        f"- 补丁数: {len(patches)}",
    ])

    if patch_names:
        lines.append(f"\n### 补丁列表")
        for pn in patch_names:
            lines.append(f"- {pn}")

    lines.extend([
        f"\n## 环境要求",
        f"- HarmonyOS/OpenHarmony aarch64",
        f"- `{project.name}/usr/local/bin` in PATH\n",
    ])

    rn.write_text("\n".join(lines), encoding="utf-8")
    log_ok(f"  RELEASENOTE.md 已生成 ({len(lines)} 行)")

    # Phase 3: Required files check
    log_info("  Phase 3: 必填文件校验...")
    missing = 0

    # Software level
    for f in ["README.md", "RELEASENOTE.md", "install.sh"]:
        p = sw_dir / f
        if not p.exists() or len(p.read_text(encoding="utf-8", errors="replace").splitlines()) < 5:
            log_warn(f"  ⚠️ 软件级缺失: {f}")
            missing += 1

    # Version level files
    for f in ["manifest.yaml", "PROGRESS.md"]:
        p = ver_dir / f
        if not p.exists() or len(p.read_text(encoding="utf-8", errors="replace").splitlines()) < 5:
            log_warn(f"  ⚠️ 版本级缺失: {f}")
            missing += 1

    # Version level dirs
    for d in ["patches", "reports", "packaging"]:
        if not (ver_dir / d).is_dir():
            log_warn(f"  ⚠️ 目录缺失: {d}")
            missing += 1

    # Packaging deliverables (only for success/partial)
    if status in ("success", "partial"):
        rel_tars = list((ver_dir / "packaging").glob("*-ohos-aarch64.tar.gz"))
        debug_tars = list((ver_dir / "packaging").glob("*-debug.tar.gz"))
        if not rel_tars:
            log_warn("  ⚠️ 缺少 release tar.gz")
            missing += 1
        if not debug_tars:
            log_warn("  ⚠️ 缺少 debug tar.gz")

    # Phase 4: Consistency check
    log_info("  Phase 4: 一致性检查...")
    issues = 0

    # Status consistency
    progress = ver_dir / "PROGRESS.md"
    if progress.exists():
        pc = progress.read_text(encoding="utf-8", errors="replace")
        progress_status = "unknown"
        for m in re.finditer(r'(?:状态|status)[：:]\s*(.+)', pc, re.I):
            progress_status = m.group(1).strip()
        if progress_status != "unknown" and status not in progress_status:
            log_warn(f"  ⚠️ 状态不一致: PROGRESS={progress_status} vs manifest={status}")
            issues += 1
        if "### 对话 #" not in pc:
            log_warn("  ⚠️ PROGRESS.md 无对话记录")
            issues += 1

    # Patch count consistency
    mf_patches = str(mf.get("patches_applied", ""))
    if mf_patches:
        mf_count = len([x for x in mf_patches.strip("[]").split(",") if x.strip()])
        disk_count = len(list((ver_dir / "patches").glob("000*.patch")))
        if mf_count != disk_count:
            log_warn(f"  ⚠️ 补丁数不一致: manifest={mf_count} vs disk={disk_count}")
            issues += 1

    # Phase 5: Report
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
