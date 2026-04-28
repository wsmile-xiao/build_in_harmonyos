"""Generate SUMMARY.md from compilation archives.

Reads archives/_index.yaml and per-software manifest.yaml files to produce
a human-readable compatibility overview document.

No external dependencies — uses a simple line-by-line YAML parser inspired
by the _parse_manifest pattern in finalize_archive.py.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from .utils import find_project_dir, log_info, log_ok, log_warn

# ── Build-system display names ──
BUILD_SYSTEM_NAMES = {
    "autotools": "Autotools",
    "cmake": "CMake",
    "custom-perl": "Custom Perl",
    "makefile": "Makefile",
    "meson": "Meson",
    "script": "Script",
}

# ── Status badges ──
STATUS_BADGE = {
    "published": "✅ 已发布",
    "built": "✅ 已编译",
    "failed": "❌ 编译失败",
    "archived": "📦 已归档",
}

# ── Compatibility level icons ──
COMPAT_LEVEL = {
    "high": "🟢 高",
    "medium": "🟡 中",
    "low": "🔴 低",
    "built": "🟡 中",
    "unknown": "",
    "": "",
}


# ═══════════════════════════════════════════════════════
# Simple YAML parsers (no PyYAML)
# ═══════════════════════════════════════════════════════

def _parse_yaml_simple(path: Path) -> dict:
    """Simple YAML parser for flat key-value files (manifest.yaml, etc.).

    Handles:
    - # comment lines
    - key: value pairs (scalar values)
    - key: followed by indented list items (- item)
    - Quoted strings stripped
    - Multi-line values (| or >)
    """
    data: dict = {}
    if not path.exists():
        return data

    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    current_key: str | None = None
    current_list_key: str | None = None
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty / comment lines
        if not stripped or stripped.startswith("#"):
            current_key = None
            i += 1
            continue

        # Indented line
        if line and line[0] in (" ", "\t"):
            # Part of a multi-line value or nested structure
            if current_list_key is not None:
                if stripped.startswith("- "):
                    item = stripped[2:].strip()
                    # Check if item has inline key: value (e.g. "- file: name")
                    if ": " in item:
                        # Nested dict item — store raw for now
                        data.setdefault(current_list_key, []).append(item)
                    else:
                        data.setdefault(current_list_key, []).append(item)
                else:
                    # Nested key within list item — skip (not needed for summary)
                    pass
            elif current_key is not None:
                # Append continuation to current scalar value
                data[current_key] = data.get(current_key, "") + "\n" + stripped
            i += 1
            continue

        # Top-level key: value
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if val.startswith("|") or val.startswith(">"):
                # Multi-line block — store the key but don't use value
                current_key = key
                current_list_key = None
                data[key] = ""
                i += 1
                continue

            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]

            if val:
                data[key] = val
                current_key = None
                current_list_key = None
            else:
                # Empty value — might be followed by list items
                current_key = None
                current_list_key = key
                data.setdefault(key, [])
        else:
            current_key = None
            current_list_key = None

        i += 1

    return data


def _parse_index_yaml(path: Path) -> list[dict]:
    """Parse archives/_index.yaml into a list of entry dicts.

    Handles the list format:
        software_index:
          - software: name
            version: "1.0"
            ...

    And the legacy dict format:
        software_index:
          software_name:
            versions: ["1.0", "2.0"]
            status: success
            ...
    """
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    # Find the software_index: section
    entries: list[dict] = []
    in_index = False
    in_dict_format = False
    current_entry: dict = {}
    current_software_name: str | None = None
    current_sub_key: str | None = None

    for line in lines:
        stripped = line.strip()

        # Skip empty / comment
        if not stripped or stripped.startswith("#"):
            continue

        # Detect top-level software_index:
        if not in_index:
            if stripped.startswith("software_index:"):
                in_index = True
                # Determine format by looking at the next non-empty line
                continue

        if not in_index:
            continue

        # Calculate indent
        indent = len(line) - len(line.lstrip())

        # If we're at top-level (no indent), we've exited the software_index section
        if indent == 0:
            break

        # Inside software_index, first level of indentation
        if indent == 2:
            # Could be "- software: ..." (list) or "software_name:" (dict)
            if stripped.startswith("- "):
                # List format entry
                # Save previous entry
                if current_entry:
                    entries.append(current_entry)
                current_entry = {}
                item_content = stripped[2:].strip()
                if ": " in item_content:
                    k, _, v = item_content.partition(":")
                    v = v.strip().strip('"').strip("'")
                    current_entry[k.strip()] = v
                current_sub_key = None
                continue
            else:
                # Dict format: "software_name:"
                if ":" in stripped:
                    k, _, v = stripped.partition(":")
                    k = k.strip()
                    v = v.strip()
                    if not v:
                        # This is a sub-section key (dict format)
                        # Save previous entry if any
                        if current_entry and current_software_name:
                            entries.append(current_entry)
                            current_entry = {}
                        current_software_name = k
                        current_sub_key = None
                        in_dict_format = True
                    else:
                        current_sub_key = k
                continue

        # Deeper indentation (4+ spaces)
        if indent >= 4:
            if in_dict_format and current_software_name:
                # Parsing dict format values like:
                #   software_name:
                #     versions: ["1.0", "2.0"]
                #     status: success
                if ": " in stripped:
                    k, _, v = stripped.partition(":")
                    k = k.strip()
                    v = v.strip()
                    # Handle versions: ["1.0", "2.0"]
                    if k == "versions":
                        # Parse bracket list
                        if v.startswith("["):
                            v = v.strip("[]")
                            versions = [x.strip().strip('"').strip("'") for x in v.split(",") if x.strip()]
                            current_entry.setdefault("_versions", []).extend(versions)
                        else:
                            current_entry.setdefault("_versions", []).append(v.strip('"').strip("'"))
                    else:
                        current_entry[k] = v.strip('"').strip("'")
                    # Always store software name
                    if "software" not in current_entry:
                        current_entry["software"] = current_software_name
                elif stripped.startswith("- "):
                    item = stripped[2:].strip().strip('"').strip("'")
                    if current_sub_key == "versions":
                        current_entry.setdefault("_versions", []).append(item)
            elif current_entry and indent >= 4:
                # List format: additional key: value on continuation lines
                if ": " in stripped:
                    k, _, v = stripped.partition(":")
                    v = v.strip().strip('"').strip("'")
                    current_entry[k.strip()] = v

    # Save last entry
    if current_entry:
        entries.append(current_entry)

    # Convert dict format entries to flat entries (one per version)
    result: list[dict] = []
    for e in entries:
        if "_versions" in e:
            versions = e.pop("_versions")
            for ver in versions:
                flat = dict(e)
                flat["version"] = str(ver)
                result.append(flat)
        else:
            result.append(e)

    return result


# ═══════════════════════════════════════════════════════
# Manifest helpers
# ═══════════════════════════════════════════════════════

def _load_manifest(archives_dir: Path, software: str, version: str) -> dict:
    """Load manifest.yaml for a specific software version."""
    first_char = software[0].lower()
    manifest_path = archives_dir / first_char / software / version / "manifest.yaml"
    return _parse_yaml_simple(manifest_path)


def _get_patch_count(manifest: dict, archives_dir: Path,
                     software: str, version: str, index_patches=None) -> int | str:
    """Get patch count from manifest or fallback to file counting."""
    if index_patches is not None:
        try:
            return int(index_patches)
        except (ValueError, TypeError):
            pass

    # Schema A: patches_applied list
    patches_a = manifest.get("patches_applied", [])
    if patches_a:
        if isinstance(patches_a, list):
            return len(patches_a)
        try:
            return int(patches_a)
        except (ValueError, TypeError):
            pass

    # Schema B: build.patches
    build = manifest.get("build", {})
    if isinstance(build, dict):
        patches_b = build.get("patches", [])
        if patches_b:
            if isinstance(patches_b, list):
                return len(patches_b)
            try:
                return int(patches_b)
            except (ValueError, TypeError):
                pass

    # Fallback: count .patch files on disk
    first_char = software[0].lower()
    patches_dir = archives_dir / first_char / software / version / "patches"
    if patches_dir.is_dir():
        return len([f for f in patches_dir.iterdir() if f.suffix == ".patch"])

    return "-"


def _get_dep_info(manifest: dict) -> str:
    """Extract dependency info from manifest for display."""
    if not manifest:
        return "-"

    deps = manifest.get("dependencies", {})
    if isinstance(deps, str):
        return deps if deps else "-"

    if isinstance(deps, list):
        dep_list = [str(d) for d in deps[:5]]
        info = ",".join(dep_list)
        if len(deps) > 5:
            info += "..."
        return info if info else "-"

    if isinstance(deps, dict):
        required = deps.get("required", [])
        optional = deps.get("optional", [])
        parts: list[str] = []
        if isinstance(required, list) and required:
            parts.append(",".join(str(d) for d in required))
        if isinstance(optional, list) and optional:
            opt_str = ",".join(str(d) for d in optional[:3])
            if len(optional) > 3:
                opt_str += "..."
            parts.append(opt_str)
        return "；".join(parts) if parts else "-"

    # Fallback: check build.dependencies
    build = manifest.get("build", {})
    if isinstance(build, dict):
        deps_b = build.get("dependencies", [])
        if isinstance(deps_b, list) and deps_b:
            info = ",".join(str(d) for d in deps_b[:5])
            if len(deps_b) > 5:
                info += "..."
            return info if info else "-"

    return "-"


# ═══════════════════════════════════════════════════════
# Core: generate SUMMARY.md
# ═══════════════════════════════════════════════════════

def _scan_archives_dir(archives_dir: Path) -> list[dict]:
    """Scan archives/ directory for all manifest.yaml files and return entries."""
    entries: list[dict] = []
    if not archives_dir.is_dir():
        return entries

    for letter_dir in sorted(archives_dir.iterdir()):
        if not letter_dir.is_dir() or letter_dir.name.startswith("_"):
            continue
        for sw_dir in sorted(letter_dir.iterdir()):
            if not sw_dir.is_dir():
                continue
            for ver_dir in sorted(sw_dir.iterdir()):
                if not ver_dir.is_dir():
                    continue
                manifest_path = ver_dir / "manifest.yaml"
                if manifest_path.exists():
                    manifest = _parse_yaml_simple(manifest_path)
                    # Extract software name — handle nested dict/list gracefully
                    sw = manifest.get("software", sw_dir.name)
                    if not isinstance(sw, str):
                        sw = sw_dir.name
                    # Extract version — handle nested dict/list gracefully
                    ver = manifest.get("version", ver_dir.name)
                    if not isinstance(ver, str):
                        ver = ver_dir.name
                    # Extract build_system — may be under build_config
                    bs = manifest.get("build_system", "")
                    if not isinstance(bs, str):
                        bs = ""
                    if not bs:
                        bc = manifest.get("build_config", {})
                        if isinstance(bc, dict):
                            bs = bc.get("build_system", "")
                            if not isinstance(bs, str):
                                bs = ""
                    # Extract status — strip '#final' etc. suffixes
                    status = manifest.get("status", "unknown")
                    if isinstance(status, str) and "#" in status:
                        status = status.split("#")[0]
                    elif not isinstance(status, str):
                        status = "unknown"
                    entry = {
                        "software": sw,
                        "version": ver,
                        "letter": letter_dir.name,
                        "status": status,
                        "build_system": bs,
                        "path": f"archives/{letter_dir.name}/{sw_dir.name}/{ver_dir.name}",
                    }
                    # Propagate compatibility if present in manifest
                    compat = manifest.get("compatibility", "")
                    if isinstance(compat, dict):
                        entry["compatibility"] = compat.get("level", "")
                    elif isinstance(compat, str):
                        entry["compatibility"] = compat
                    entries.append(entry)
    return entries


def generate_summary(pdir: str | None = None) -> str:
    """Generate SUMMARY.md content and write it to the project root.

    Uses a dual data source:
    1. _index.yaml as the base data source (if it exists)
    2. Scans archives/ directory for manifest.yaml files to find
       entries missing from _index.yaml
    3. Removes entries from _index.yaml that no longer exist on disk
    """
    project_dir = Path(pdir) if pdir else Path(find_project_dir())
    archives_dir = project_dir / "archives"
    index_path = archives_dir / "_index.yaml"
    output_path = project_dir / "SUMMARY.md"

    # ── Step 1: Load entries from _index.yaml ──
    entries = _parse_index_yaml(index_path)

    # ── Step 2: Scan archives/ for manifest.yaml files ──
    archive_entries = _scan_archives_dir(archives_dir)

    # Build lookup by normalized path (without "archives/" prefix)
    archive_path_set: set[str] = set()
    archive_by_path: dict[str, dict] = {}
    for ae in archive_entries:
        p = ae.get("path", "").removeprefix("archives/")
        archive_path_set.add(p)
        archive_by_path[p] = ae

    # ── Step 3: Build path set from _index.yaml entries ──
    index_path_set: set[str] = set()
    for entry in entries:
        p = entry.get("path", "").removeprefix("archives/")
        if p:
            index_path_set.add(p)

    # ── Step 4: Remove entries not on disk, add entries missing from _index ──
    # Filter out entries whose archive path no longer exists on disk
    entries = [e for e in entries
               if e.get("path", "").removeprefix("archives/") in archive_path_set]

    # Add entries found in archives but missing from _index.yaml
    for p, ae in archive_by_path.items():
        if p not in index_path_set:
            entries.append(ae)
            log_info(f"  从 manifest 补充: {p}")

    # ── Statistics ──
    total_versions = len(entries)
    unique_names: set[str] = set()
    by_status: dict[str, int] = defaultdict(int)
    by_build: dict[str, int] = defaultdict(int)
    grouped: dict[str, list[dict]] = defaultdict(list)

    for entry in entries:
        name = entry.get("software", "")
        unique_names.add(name)
        status = entry.get("status", "unknown")
        by_status[status] += 1
        build_sys = entry.get("build_system", "")
        if build_sys:
            by_build[build_sys] += 1
        grouped[name].append(entry)

    total_software = len(unique_names)

    # ── Build the document ──
    lines: list[str] = []

    # Header
    lines.append("# 鸿蒙平台开源软件编译兼容性总览")
    lines.append("")
    lines.append(f"> 最后更新：{datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"> 已收录软件：{total_software} 款 / {total_versions} 个版本")
    lines.append("")

    # Statistics overview
    lines.append("## 📊 总体统计")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 收录软件 | **{total_software}** 款 |")
    lines.append(f"| 软件版本 | **{total_versions}** 个 |")
    lines.append(f"| ✅ 已发布 | {by_status.get('published', 0)} |")
    lines.append(f"| ✅ 已编译 | {by_status.get('built', 0)} |")
    lines.append(f"| ❌ 编译失败 | {by_status.get('failed', 0)} |")
    lines.append("")

    if by_build:
        lines.append("| 构建系统 | 数量 |")
        lines.append("|----------|------|")
        for bs, count in sorted(by_build.items(), key=lambda x: -x[1]):
            lines.append(f"| {BUILD_SYSTEM_NAMES.get(bs, bs)} | {count} |")
        lines.append("")

    # Software overview table
    lines.append("## 📋 软件兼容性一览")
    lines.append("")
    lines.append("| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |")
    lines.append("|------|------|------|--------|----------|--------|------|------|")

    for name in sorted(grouped.keys()):
        version_entries = grouped[name]
        latest = version_entries[-1]
        latest_version = str(latest.get("version", "unknown"))
        status = latest.get("status", "unknown")
        build_sys = latest.get("build_system", "")
        path = latest.get("path", "")
        compat_raw = latest.get("compatibility", "")
        index_patches = latest.get("patches")

        # Load manifest for extra info
        manifest = _load_manifest(archives_dir, name, latest_version)
        patch_count = _get_patch_count(manifest, archives_dir,
                                       name, latest_version, index_patches)
        dep_info = _get_dep_info(manifest)

        # Compatibility level
        compat_str = COMPAT_LEVEL.get(compat_raw, "")
        if not compat_str and manifest:
            compat = manifest.get("compatibility", {})
            if isinstance(compat, dict):
                compat_str = COMPAT_LEVEL.get(compat.get("level", ""), "")
            elif isinstance(compat, str):
                compat_str = COMPAT_LEVEL.get(compat, "")

        # Version list — avoid duplicate version strings when
        # multiple paths exist for the same software+version
        seen_versions: set[str] = set()
        unique_vers: list[str] = []
        for e in version_entries:
            v = str(e.get("version", ""))
            if v not in seen_versions:
                seen_versions.add(v)
                unique_vers.append(v)
        version_str = "、".join(unique_vers) if unique_vers else latest_version

        status_str = STATUS_BADGE.get(status, status)
        detail_link = f"[📄]({path}/)"

        lines.append(
            f"| **{name}** | {version_str} | {status_str} | {compat_str} "
            f"| {BUILD_SYSTEM_NAMES.get(build_sys, build_sys)} "
            f"| {patch_count} | {dep_info} | {detail_link} |"
        )

    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        "*本文档由 `ohc summary` 从编译档案自动生成，请勿手动编辑。*"
    )
    lines.append("")
    lines.append("Copyright (c) 2024-2026 OpenHarmony PC Developer社区")

    content = "\n".join(lines)

    # Write to file
    output_path.write_text(content, encoding="utf-8")
    return content


# ═══════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════

def summary_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc summary"""
    parser = argparse.ArgumentParser(
        prog="ohc summary",
        description="从编译档案生成 SUMMARY.md 总览文档",
    )
    parser.add_argument(
        "--project-dir", "-p",
        default=None,
        help="项目根目录（默认自动检测）",
    )
    args = parser.parse_args(argv)
    pdir = getattr(args, "project_dir", None)

    log_info("生成 SUMMARY.md ...")
    try:
        content = generate_summary(pdir=pdir)
        log_ok(f"SUMMARY.md 生成完成 ({len(content)} 字符)")
        return 0
    except Exception as e:
        log_warn(f"SUMMARY.md 生成失败: {e}")
        return 1
