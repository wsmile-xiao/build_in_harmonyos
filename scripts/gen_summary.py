#!/usr/bin/env python3
"""
gen_summary.py - 从编译档案生成人可读的 summary.md

读取 archives/_index.yaml 和各软件的 manifest.yaml，
生成面向人类的软件兼容性总览文档。
"""

import os
import sys
import yaml
from datetime import datetime

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

# 状态徽标
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
    "": "未评估",
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
        # 有些 manifest.yaml 包含多个 YAML 文档（用 --- 分隔），只解析第一个
        docs = list(yaml.safe_load_all(content))
        return docs[0] if docs else None


def count_patches(patches):
    """统计补丁数量"""
    if not patches:
        return 0
    return len(patches)


def generate_summary():
    """生成完整的 SUMMARY.md"""
    index = load_index()
    software_index = index.get("software_index", {})
    statistics = index.get("statistics", {})

    lines = []

    # 头部
    lines.append("# 鸿蒙平台开源软件编译兼容性总览")
    lines.append("")
    lines.append(f"> 最后更新：{datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"> 已收录软件：{statistics.get('total_software', 0)} 款 / "
                 f"{statistics.get('total_versions', 0)} 个版本")
    lines.append("")

    # 统计概览
    by_status = statistics.get("by_status", {})
    lines.append("## 📊 总体统计")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|------|------|")
    lines.append(f"| 收录软件 | **{statistics.get('total_software', 0)}** 款 |")
    lines.append(f"| 软件版本 | **{statistics.get('total_versions', 0)}** 个 |")
    lines.append(f"| ✅ 完全成功 | {by_status.get('success', 0)} |")
    lines.append(f"| ⚠️ 部分成功 | {by_status.get('partial', 0)} |")
    lines.append(f"| ❌ 编译失败 | {by_status.get('failed', 0)} |")
    lines.append("")

    by_build = statistics.get("by_build_system", {})
    if by_build:
        lines.append("| 构建系统 | 数量 |")
        lines.append("|----------|------|")
        for bs, count in sorted(by_build.items(), key=lambda x: -x[1]):
            lines.append(f"| {BUILD_SYSTEM_NAMES.get(bs, bs)} | {count} |")
        lines.append("")

    # 快速总览表
    lines.append("## 📋 软件兼容性一览")
    lines.append("")
    lines.append("| 软件 | 版本 | 状态 | 兼容性 | 构建系统 | 补丁数 | 依赖 | 详情 |")
    lines.append("|------|------|------|--------|----------|--------|------|------|")

    # 按软件名字母排序
    sorted_software = sorted(software_index.items(), key=lambda x: x[0])
    for name, info in sorted_software:
        versions = info.get("versions", [])
        status = info.get("status", "unknown")
        build_sys = info.get("build_system", "")
        path = info.get("path", "")

        # 取最新版本的 manifest
        latest_version = versions[-1] if versions else "unknown"
        manifest = load_manifest(name, latest_version)

        compat_level = ""
        patch_count = "-"
        dep_info = "-"
        if manifest:
            compat = manifest.get("compatibility", {}) or {}
            compat_level = COMPAT_LEVEL.get(compat.get("level", ""), "")
            patch_count = count_patches(manifest.get("patches_applied", []))
            deps = manifest.get("dependencies", {}) or {}
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
            if dep_parts:
                dep_info = "；".join(dep_parts)

        # 详情链接
        detail_link = f"[📄]({path}/{latest_version}/)"
        if len(versions) > 1:
            version_str = "、".join(versions)
        else:
            version_str = latest_version

        status_str = STATUS_BADGE.get(status, status)

        lines.append(
            f"| **{name}** | {version_str} | {status_str} | {compat_level} "
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


def main():
    print(f"读取索引: {INDEX_FILE}")
    content = generate_summary()
    print(f"写入: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"完成! 共 {len(content)} 字符")


if __name__ == "__main__":
    main()
