#!/usr/bin/env python3
"""migrate_kv_to_yaml.py — 批量将 .kv 知识条目转为 .yaml 格式。

渐进迁移工具：将 knowledge/graph/ 下的 .kv 文件转换为 .yaml 文件，
保留原 .kv 文件作为备份。

特性：
  - 自动识别单条目文件 (E*.kv) 和多条目文件 (principles.kv)
  - 将管道分隔列表 (trigger_tool, phase, error_signature, category) 转为 YAML 列表
  - 将逗号分隔列表 (match_keywords, principles, scope) 转为 YAML 列表
  - 将方括号列表 (causes, caused_by, similar_to, ...) 转为 YAML 列表
  - 不删除原 .kv 文件

用法:
    python3 scripts/migrate_kv_to_yaml.py                    # 迁移 knowledge/graph/ 下所有 .kv
    python3 scripts/migrate_kv_to_yaml.py knowledge/graph/   # 指定目录
    python3 scripts/migrate_kv_to_yaml.py knowledge/graph/E001.kv  # 迁移单个文件
    python3 scripts/migrate_kv_to_yaml.py --dry-run          # 预览，不写入文件
"""
from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path

# ── 确保能导入 ohc 包 ──────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from ohc.models import (
    parse_kv_file,
    parse_multi_kv_file,
    _parse_pipe_list,
    _parse_comma_list,
    _parse_bracket_list,
)

# ── 列表字段定义 ────────────────────────────────────────
# 在 KV 格式中使用不同分隔符的字段，迁移到 YAML 时统一转为列表

# 管道分隔 (|): trigger_tool, phase, error_signature, category
PIPE_LIST_FIELDS: set[str] = {
    "trigger_tool",
    "phase",
    "error_signature",
    "category",
}

# 逗号分隔 (,): match_keywords, principles, scope
COMMA_LIST_FIELDS: set[str] = {
    "match_keywords",
    "principles",
    "scope",
}

# 方括号格式 ([]): causes, caused_by, similar_to, conflicts_with, prerequisite_of
BRACKET_LIST_FIELDS: set[str] = {
    "causes",
    "caused_by",
    "similar_to",
    "conflicts_with",
    "prerequisite_of",
}

ALL_LIST_FIELDS = PIPE_LIST_FIELDS | COMMA_LIST_FIELDS | BRACKET_LIST_FIELDS


def _convert_list_fields(data: dict[str, str]) -> dict:
    """将 KV dict 中的列表字段从字符串转为 Python list。

    非列表字段保持为字符串。空字符串转为空列表（对于列表字段）。
    """
    result: dict = {}
    for key, value in data.items():
        if key in PIPE_LIST_FIELDS:
            result[key] = _parse_pipe_list(value)
        elif key in COMMA_LIST_FIELDS:
            result[key] = _parse_comma_list(value)
        elif key in BRACKET_LIST_FIELDS:
            result[key] = _parse_bracket_list(value)
        else:
            result[key] = value
    return result


def _is_multi_entry(filepath: str) -> bool:
    """检测 .kv 文件是否包含多个条目（多个 id: 行）。"""
    id_count = 0
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("id:") and not stripped.startswith("#"):
                id_count += 1
                if id_count > 1:
                    return True
    return False


def migrate_single_entry(filepath: str, dry_run: bool = False) -> bool:
    """转换单条目 .kv 文件为 .yaml。

    Returns: True if .yaml was written (or would be in dry_run), False if skipped.
    """
    yaml_path = filepath.rsplit(".", 1)[0] + ".yaml"

    raw = parse_kv_file(filepath)
    if not raw:
        print(f"  ⚠ SKIP (empty): {filepath}")
        return False

    converted = _convert_list_fields(raw)

    if dry_run:
        print(f"  [DRY-RUN] Would write: {yaml_path}")
        return True

    _write_yaml(yaml_path, converted)
    print(f"  ✓ {os.path.basename(filepath)} → {os.path.basename(yaml_path)}")
    return True


def migrate_multi_entry(filepath: str, dry_run: bool = False) -> bool:
    """转换多条目 .kv 文件为 .yaml（输出为 YAML 列表）。

    Returns: True if .yaml was written (or would be in dry_run), False if skipped.
    """
    yaml_path = filepath.rsplit(".", 1)[0] + ".yaml"

    entries = parse_multi_kv_file(filepath)
    if not entries:
        print(f"  ⚠ SKIP (empty): {filepath}")
        return False

    converted_list = [_convert_list_fields(entry) for entry in entries]

    if dry_run:
        print(f"  [DRY-RUN] Would write: {yaml_path} ({len(converted_list)} entries)")
        return True

    _write_yaml(yaml_path, converted_list)
    print(f"  ✓ {os.path.basename(filepath)} → {os.path.basename(yaml_path)} "
          f"({len(converted_list)} entries)")
    return True


def _write_yaml(yaml_path: str, data) -> None:
    """写入 YAML 文件。"""
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is not installed. Install with: pip3 install pyyaml")
        sys.exit(1)

    with open(yaml_path, "w", encoding="utf-8") as f:
        # 写入文件头注释
        basename = os.path.basename(yaml_path)
        f.write(f"# {basename} — auto-generated from {basename.rsplit('.', 1)[0]}.kv\n")
        f.write(f"# Migrated by migrate_kv_to_yaml.py\n")
        f.write(f"# Original .kv file preserved as backup.\n\n")
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )


def find_kv_files(path: str) -> list[str]:
    """查找指定路径下的所有 .kv 文件。

    如果 path 是文件，返回 [path]（如果是 .kv）。
    如果 path 是目录，递归查找所有 .kv 文件。
    """
    if os.path.isfile(path):
        if path.endswith(".kv"):
            return [path]
        else:
            print(f"ERROR: {path} is not a .kv file")
            sys.exit(1)

    if os.path.isdir(path):
        kv_files = []
        for root, dirs, files in os.walk(path):
            for fname in sorted(files):
                if fname.endswith(".kv"):
                    kv_files.append(os.path.join(root, fname))
        return sorted(kv_files)

    print(f"ERROR: {path} does not exist")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="批量将 .kv 知识条目转为 .yaml 格式（保留 .kv 原文件）"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="要迁移的 .kv 文件或目录（默认: knowledge/graph/）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只打印将要执行的操作，不写入文件",
    )
    args = parser.parse_args()

    # 默认路径：项目根目录下的 knowledge/graph/
    if args.path is None:
        project_root = os.path.dirname(SCRIPTS_DIR)
        default_dir = os.path.join(project_root, "knowledge", "graph")
        if os.path.isdir(default_dir):
            target = default_dir
        else:
            print(f"ERROR: 默认目录 {default_dir} 不存在，请指定路径")
            return 1
    else:
        target = args.path

    # 查找 .kv 文件
    kv_files = find_kv_files(target)
    if not kv_files:
        print(f"没有找到 .kv 文件: {target}")
        return 0

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}迁移 {len(kv_files)} 个 .kv 文件")
    print(f"目标目录: {target}")
    print()

    migrated = 0
    skipped = 0
    for kv_file in kv_files:
        if _is_multi_entry(kv_file):
            ok = migrate_multi_entry(kv_file, dry_run=args.dry_run)
        else:
            ok = migrate_single_entry(kv_file, dry_run=args.dry_run)
        if ok:
            migrated += 1
        else:
            skipped += 1

    print()
    print(f"完成: {migrated} 个文件已迁移, {skipped} 个跳过")
    if not args.dry_run:
        print("原 .kv 文件已保留作为备份。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
