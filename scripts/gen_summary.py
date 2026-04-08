#!/usr/bin/env python3
# ==============================================================================
# [Layer 3] gen_summary.py - 编译档案总结报告生成工具（AI 主导）
# ==============================================================================
# 层级: L3(辅助工具)
# 决策点: AI主导（报告内容供 AI 审阅和决策参考）
# 入口: python3 scripts/gen_summary.py（无参数，自动扫描 archives/）
# 依赖: PyYAML, archives/_index.yaml, 各 manifest.yaml
# 调用者: finish-build.sh, close-archive.sh, AI / 用户
# ==============================================================================
"""
gen_summary.py - 从编译档案生成人可读的 summary.md

读取 archives/_index.yaml 和各软件的 manifest.yaml，
生成面向人类的软件兼容性总览文档。
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVES_DIR = os.path.join(REPO_ROOT, "archives")
INDEX_FILE = os.path.join(ARCHIVES_DIR, "_index.yaml")
OUTPUT_FILE = os.path.join(REPO_ROOT, "SUMMARY.md")

# 构建系统中文映射
BUILD_SYSTEM_NAMES = {
    "autotools": "Autotools",
    "cmake": "CMake",
    "custom-perl": "Custom Perl",
    "makefile": "Makefile",
    "meson": "Meson",
    "script": "Script",
}

# 状态徽标（统一状态值体系: success / partial / failed）
STATUS_BADGE = {
    "success": "✅ 完全成功",
    "partial": "⚠️ 部分成功",
    "failed": "❌ 编译失败",
}

# 兼容性等级
COMPAT_LEVEL = {
    "high": "🟢 高",
    "medium": "🟡 中",
    "low": "🔴 低",
    "partial": "🟡 中",
    "unknown": "",
    "": "",
}


def load_index():
    """加载 _index.yaml"""
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_manifest(software, version):
    """加载指定软件版本的 manifest.yaml"""
    first_char = software[0]
    manifest_path = os.path.join(
        ARCHIVES_DIR, first_char, software, version, "manifest.yaml"
    )
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
        docs = list(yaml.safe_load_all(content))
        return docs[0] if docs else None


def get_patch_count_from_manifest(manifest, software, version):
    """从 manifest 获取补丁数量"""
    if not manifest:
        return None
    # Schema A: patches_applied
    patches_a = manifest.get("patches_applied", [])
    if patches_a:
        return len(patches_a)
    # Schema B: build.patches
    build = manifest.get("build", {}) or {}
    patches_b = build.get("patches", [])
    if patches_b:
        return len(patches_b)
    # Fallback: count actual .patch files
    first_char = software[0]
    patches_dir = os.path.join(
        ARCHIVES_DIR, first_char, software, version, "patches"
    )
    if os.path.isdir(patches_dir):
        return len([f for f in os.listdir(patches_dir) if f.endswith(".patch")])
    return None


def get_dep_info(manifest):
    """从 manifest 获取依赖信息"""
    if not manifest:
        return "-"
    deps = manifest.get("dependencies", {}) or {}
    if isinstance(deps, list):
        dep_info = ",".join(str(d) for d in deps[:5])
        if len(deps) > 5:
            dep_info += "..."
        return dep_info if dep_info else "-"
    if deps:
        build_b = manifest.get("build", {}) or {}
        deps_b = build_b.get("dependencies", []) or []
        if isinstance(deps_b, list):
            dep_info = ",".join(str(d) for d in deps_b[:5])
            if len(deps_b) > 5:
                dep_info += "..."
            return dep_info if dep_info else "-"
        required = deps.get("required", []) or []
        optional = deps.get("optional", []) or []
        dep_parts = []
        if required:
            dep_parts.append(",".join(required))
        if optional:
            opt_str = ",".join(optional[:3])
            if len(optional) > 3:
                opt_str += "..."
            dep_parts.append(opt_str)
        return "；".join(dep_parts) if dep_parts else "-"
    return "-"


def generate_summary():
    """生成完整的 SUMMARY.md"""
    index = load_index()
    raw_index = index.get("software_index", [])

    # 兼容新旧格式：旧格式是 dict，新格式是 list
    if isinstance(raw_index, dict):
        entries = _convert_dict_to_flat(raw_index)
    else:
        entries = raw_index

    # 统计
    total_versions = len(entries)
    unique_names = set()
    by_status = defaultdict(int)
    by_build = defaultdict(int)
    # 按软件名分组
    grouped = defaultdict(list)
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

    lines = []

    # 头部
    lines.append("# 鸿蒙平台开源软件编译兼容性总览")
    lines.append("")
    lines.append(f"> 最后更新：{datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"> 已收录软件：{total_software} 款 / {total_versions} 个版本")
    lines.append("")

    # 统计概览
    lines.append("## 📊 总体统计")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 收录软件 | **{total_software}** 款 |")
    lines.append(f"| 软件版本 | **{total_versions}** 个 |")
    lines.append(f"| ✅ 完全成功 | {by_status.get('success', 0)} |")
    lines.append(f"| ⚠️ 部分成功 | {by_status.get('partial', 0)} |")
    lines.append(f"| ❌ 编译失败 | {by_status.get('failed', 0)} |")
    lines.append("")

    if by_build:
        lines.append("| 构建系统 | 数量 |")
        lines.append("|----------|------|")
        for bs, count in sorted(by_build.items(), key=lambda x: -x[1]):
            lines.append(f"| {BUILD_SYSTEM_NAMES.get(bs, bs)} | {count} |")
        lines.append("")

    # 软件一览表
    lines.append("## 📋 软件兼容性一览")
    lines.append("")
    lines.append("| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |")
    lines.append("|------|------|------|--------|----------|--------|------|------|")

    for name in sorted(grouped.keys()):
        versions_entries = grouped[name]
        # 取最新版本（列表最后一个）来获取详细信息
        latest = versions_entries[-1]
        latest_version = str(latest.get("version", "unknown"))
        status = latest.get("status", "unknown")
        build_sys = latest.get("build_system", "")
        path = latest.get("path", "")
        compat_raw = latest.get("compatibility", "")

        # 尝试从 manifest 获取更多信息
        manifest = load_manifest(name, latest_version)
        patch_count = latest.get("patches")
        if patch_count is None and manifest:
            patch_count = get_patch_count_from_manifest(manifest, name, latest_version)
        if patch_count is None:
            patch_count = "-"
        dep_info = get_dep_info(manifest)

        # 兼容性等级
        compat_str = COMPAT_LEVEL.get(compat_raw, "")
        if not compat_str and manifest:
            compat = manifest.get("compatibility", {}) or {}
            compat_str = COMPAT_LEVEL.get(compat.get("level", ""), "")

        # 版本列表
        if len(versions_entries) > 1:
            version_str = "、".join(e.get("version", "") for e in versions_entries)
        else:
            version_str = latest_version

        status_str = STATUS_BADGE.get(status, status)
        detail_link = f"[📄]({path}/)"

        lines.append(
            f"| **{name}** | {version_str} | {status_str} | {compat_str} "
            f"| {BUILD_SYSTEM_NAMES.get(build_sys, build_sys)} "
            f"| {patch_count} | {dep_info} | {detail_link} |"
        )

    lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append("*本文档由 `scripts/gen_summary.py` 从编译档案自动生成，请勿手动编辑。*")
    lines.append("")
    lines.append(f"Copyright (c) 2024-2026 OpenHarmony PC Developer社区")

    return "\n".join(lines)


def _convert_dict_to_flat(software_index):
    """兼容旧格式：将 dict 格式转为 flat list"""
    entries = []
    for name, info in software_index.items():
        versions = info.get("versions", [])
        status = info.get("status", "unknown")
        build_sys = info.get("build_system", "")
        path = info.get("path", "")
        if not versions:
            versions = ["unknown"]
        for ver in versions:
            entries.append({
                "software": name,
                "version": str(ver),
                "status": status,
                "build_system": build_sys,
                "path": path,
            })
    return entries


def main():
    print(f"读取索引: {INDEX_FILE}")
    content = generate_summary()
    print(f"写入: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"完成! 共 {len(content)} 字符")


if __name__ == "__main__":
    main()
