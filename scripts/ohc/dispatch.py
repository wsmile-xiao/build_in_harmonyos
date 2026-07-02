"""多任务编译调度系统 — 拓扑排序、子任务目标生成、批量计划。

支持将多个软件的编译任务按依赖关系排序，生成分阶段的 createSubTask 调用指令，
供主任务 AI 并行派发异步子任务。

Usage:
    python3 ohc-run.py dispatch plan <软件1> <软件2> ...
    python3 ohc-run.py dispatch status <软件1> <软件2> ...
    python3 ohc-run.py dispatch objective <软件> <版本>
"""
from __future__ import annotations

import os
import sys
from collections import deque
from pathlib import Path
from typing import Optional

import yaml

from .dependency_resolver import _KNOWN_DEPS, get_available_version
from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


# ═══════════════════════════════════════════════════════
# Registry helpers
# ═══════════════════════════════════════════════════════

def _load_registry() -> dict:
    """Load software-registry.yaml and return the registry dict."""
    project_dir = find_project_dir()
    reg_path = os.path.join(project_dir, "scripts", "software-registry.yaml")
    if not os.path.isfile(reg_path):
        return {}
    try:
        with open(reg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("registry", {}) if data else {}
    except Exception:
        return {}


def _get_registry_entry(software: str) -> dict:
    """Get a single entry from software-registry.yaml."""
    registry = _load_registry()
    return registry.get(software, {})


def _get_version(software: str) -> str:
    """Get the best known version for a software.

    Try registry first, then BUILTIN_INDEX, then fallback.
    """
    entry = _get_registry_entry(software)
    # Walk all versions in the archive dir to find the latest
    project_dir = find_project_dir()
    archive_base = os.path.join(
        project_dir, "archives", software[0].lower(), software
    )
    if os.path.isdir(archive_base):
        versions = sorted(
            [d for d in os.listdir(archive_base)
             if os.path.isdir(os.path.join(archive_base, d))],
            reverse=True,
        )
        if versions:
            return versions[0]
    # Fallback to runtime index (cmd-pkgs)
    try:
        ver = get_available_version(software)
        return ver or ""
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════
# 1. Topological sort (Kahn's algorithm)
# ═══════════════════════════════════════════════════════

def topological_sort(software_list: list[str]) -> list[str]:
    """对软件列表进行拓扑排序（Kahn 算法）。

    从 dependency_resolver._KNOWN_DEPS 获取依赖关系。
    如果依赖不在任务列表中（假设已安装），跳过。

    Args:
        software_list: 需要编译的软件名称列表。

    Returns:
        按依赖顺序排列的软件列表（无依赖的在前）。

    Raises:
        ValueError: 如果检测到循环依赖。
    """
    # Build adjacency and in-degree for only the requested software
    software_set = set(software_list)
    in_degree: dict[str, int] = {s: 0 for s in software_set}
    dependents: dict[str, list[str]] = {s: [] for s in software_set}

    for sw in software_set:
        deps_info = _KNOWN_DEPS.get(sw, {})
        required = deps_info.get("required", [])
        for dep in required:
            if dep in software_set:
                # dep → sw edge: sw depends on dep
                dependents[dep].append(sw)
                in_degree[sw] += 1
            # If dep not in software_set, assume already installed — skip

    # Kahn's algorithm
    queue: deque[str] = deque()
    for sw in software_set:
        if in_degree[sw] == 0:
            queue.append(sw)

    sorted_list: list[str] = []
    while queue:
        node = queue.popleft()
        sorted_list.append(node)
        for neighbor in dependents[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_list) != len(software_set):
        remaining = software_set - set(sorted_list)
        raise ValueError(
            f"检测到循环依赖，涉及软件: {', '.join(sorted(remaining))}"
        )

    return sorted_list


# ═══════════════════════════════════════════════════════
# 2. Generate subtask objective
# ═══════════════════════════════════════════════════════

def generate_subtask_objective(
    software: str, version: str, project_root: str | None = None
) -> str:
    """生成子任务的 objective 文本，供 createSubTask 使用。

    Args:
        software: 软件名称。
        version: 版本号。
        project_root: 项目根目录（默认自动检测）。

    Returns:
        完整的 objective 文本字符串。
    """
    project_root = project_root or find_project_dir()
    entry = _get_registry_entry(software)
    known_issues = entry.get("known_issues", [])
    build_system = entry.get("build_system", "autotools")

    # Format known_issues as bullet list
    if known_issues:
        issues_text = "\n".join(f"   - {iss}" for iss in known_issues)
    else:
        issues_text = "   - 无已知问题"

    letter = software[0].lower()

    objective = f"""你是 OpenHarmony 三方库编译协作者，负责**端到端**编译 {software} {version}。

## 第一步：加载技能（必须，不可跳过）

调用 `LoadSkill` 加载 `openharmony-compile-agent` 技能。加载后你会获得完整的 SKILL.md，它是你执行编译的**唯一权威指南**。所有流程、铁律、命令格式、失败处理均以 SKILL.md 为准。

## 第二步：⭐ 前置工具检查与自动安装（动态发现）

> **R18 扩展**：任何工具缺失，**优先从 cmd-pkgs 自动安装**。随着 cmd-pkgs 包库扩展，可用工具会动态增长。

执行 init-build 后，在 configure 之前：

1. **运行通用工具检查**：
   ```bash
   # 使用 SKILL 内置的通用检查函数（不硬编码特定工具）
   python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --check-tools
   
   # 或手动检查：
   for tool in sed gawk grep find automake libtool pkg-config make; do
     if which $tool >/dev/null 2>&1; then
       version=$(timeout 5 $tool --version 2>&1 | head -1)
       echo "$tool: $version"
     else
       echo "$tool: ❌ 未安装"
     fi
   done
   ```

2. **收到 "command not found" 或工具缺失时**：
   - 脚本会自动调用 `auto_install_missing_tools_from_log()`
   - 从错误日志提取缺失工具名 → 查 cmd-pkgs → 自动安装 → 重试
   - 无需人工判断具体是哪个工具

3. **预编译包动态列表获取**：
   ```bash
   # 从远程获取最新列表（每次都刷新，不依赖本地缓存）
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/raw/main/README.md | grep -E "^\\|[^|]+\\|"
   
   # 或使用 resolve-deps 命令
   python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --refresh
   python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --list-available
   ```

**自动安装流程**（脚本自动执行，无需人工干预）：
```
发现工具缺失 → 查 cmd-pkgs 索引 → 有预编译包 → curl install.sh | sh → 重试 configure
              ↓ 无预编译包
              → HANDOFF (build_tool_missing) → AI 手动编译依赖
```

## 第三步：按 SKILL.md 执行完整的模式 B 编译流程

加载技能并安装依赖后，**严格遵循 SKILL.md §3 核心流程**，执行端到端编译：

1. **init-build** → 下载/解压/骨架/依赖解析
2. **AI 编译（Step 2）** → configure → make → make install DESTDIR → staging 验证 → make check → package → make install（不带 DESTDIR）→ 用户验证
3. **finish（Step 3）** → refresh-patch → close-archive → verify-build → finalize-archive → check-knowledge-gap → gen_summary

关键要求（详见 SKILL.md）：
- 遇到错误时：先 `ohc-run.py engine "错误日志"` 匹配知识图谱（R12），再按匹配方案修复
- 每次修改源文件后：必须 `track-edit add` 记录（R6）
- R17 知识图谱草稿：遇到新错误模式（知识图谱无匹配），必须用 `graph add E{{N}} --draft` 创建草稿
- 所有铁律（R1-R23）以 SKILL.md 中的描述为准

## 软件信息
- 软件: {software} {version}
- 构建系统: {build_system}
- 已知问题:
{issues_text}

## 关键路径
- 项目根目录 / SKILL_ROOT: {project_root}
- 源码目录: ~/tmp/builds/{software}-{version}.work
- 归档目录: {project_root}/archives/{letter}/{software}/{version}/

## 完成标准
- finish 返回 0（manifest status=success, .packaged + .knowledge-done 标记存在）
- 如有新错误模式 → knowledge/graph/draft/ 中有对应草稿

## 输出要求
编译结果摘要：
1. 软件名、版本、最终状态（success/partial/failed）
2. 遇到的关键问题及解决方式
3. 安装的预编译依赖包列表（如有）
4. 创建的知识图谱草稿 ID（如有新发现）
"""
    return objective


# ═══════════════════════════════════════════════════════
# 3. Check task status
# ═══════════════════════════════════════════════════════

def check_task_status(software: str, version: str) -> str:
    """检查单个软件的编译任务状态。

    通过检查归档目录中的各种标记文件判断状态。

    Args:
        software: 软件名称。
        version: 版本号。

    Returns:
        状态字符串，取值:
        - "not_started": 归档目录不存在
        - "init_done": 有 manifest.yaml 但无编译结果
        - "built": 有 .staging-verified
        - "packaged": 有 .packaged
        - "knowledge_done": 有 .knowledge-done
        - "finished": manifest.yaml status=success + .packaged + .knowledge-done
        - "failed": manifest.yaml status=failed
    """
    project_dir = find_project_dir()
    letter = software[0].lower()
    archive_dir = os.path.join(
        project_dir, "archives", letter, software, version
    )

    if not os.path.isdir(archive_dir):
        return "not_started"

    manifest_path = os.path.join(archive_dir, "manifest.yaml")

    # Check manifest status
    manifest_status = None
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f) or {}
            manifest_status = manifest.get("status")
        except Exception:
            pass

    # Check marker files
    has_packaged = os.path.isfile(
        os.path.join(archive_dir, "packaging", ".packaged")
    )
    has_knowledge_done = os.path.isfile(
        os.path.join(archive_dir, ".knowledge-done")
    )
    has_staging_verified = os.path.isfile(
        os.path.join(archive_dir, ".staging-verified")
    )

    # Determine status (most specific first)
    if manifest_status == "failed":
        return "failed"

    if (manifest_status == "published" and has_packaged and has_knowledge_done):
        return "finished"

    if has_knowledge_done:
        return "knowledge_done"

    if has_packaged:
        return "packaged"

    if has_staging_verified:
        return "built"

    if os.path.isfile(manifest_path):
        return "init_done"

    return "not_started"


# ═══════════════════════════════════════════════════════
# 4. Batch status check
# ═══════════════════════════════════════════════════════

# Status display helpers
_STATUS_ICONS = {
    "not_started": "⬜",
    "init_done":   "🔵",
    "built":       "🟡",
    "packaged":    "🟠",
    "knowledge_done": "🟣",
    "finished":    "✅",
    "failed":      "❌",
}


def dispatch_status(software_list: list[str]) -> dict[str, str]:
    """批量检查软件编译状态，输出表格。

    Args:
        software_list: 软件名称列表。

    Returns:
        dict mapping software → status string.
    """
    results: dict[str, str] = {}

    print(f"\n  {'软件':<18} {'版本':<12} {'状态':<18} {'图标'}")
    print(f"  {'─' * 60}")

    for sw in software_list:
        version = _get_version(sw)
        status = check_task_status(sw, version)
        results[sw] = status
        icon = _STATUS_ICONS.get(status, "?")
        print(f"  {sw:<18} {version:<12} {status:<18} {icon}")

    print()

    # Summary
    finished_count = sum(1 for s in results.values() if s == "finished")
    failed_count = sum(1 for s in results.values() if s == "failed")
    pending_count = sum(1 for s in results.values() if s not in ("finished", "failed"))

    print(f"  总计: {len(software_list)} | ✅ 完成: {finished_count} | ❌ 失败: {failed_count} | ⏳ 进行中/待开始: {pending_count}")
    print()

    return results


# ═══════════════════════════════════════════════════════
# 5. Plan batch
# ═══════════════════════════════════════════════════════

def plan_batch(software_list: list[str]) -> list[dict]:
    """生成批量编译计划。

    执行拓扑排序，识别已完成的任务（跳过）、识别依赖未满足的任务，
    输出分阶段执行计划。

    Args:
        software_list: 软件名称列表。

    Returns:
        分阶段任务列表，每个元素: {"phase": int, "tasks": [...]}
        每个 task: {"software": str, "version": str, "status": str, "objective": str}
    """
    project_dir = find_project_dir()

    # Step 1: Topological sort
    try:
        sorted_list = topological_sort(software_list)
    except ValueError as e:
        log_fail(str(e))
        return []

    # Step 2: Build phases by dependency depth
    software_set = set(software_list)
    phase_of: dict[str, int] = {}

    def _get_phase(sw: str) -> int:
        if sw in phase_of:
            return phase_of[sw]
        deps_info = _KNOWN_DEPS.get(sw, {})
        required = deps_info.get("required", [])
        max_dep_phase = 0
        for dep in required:
            if dep in software_set:
                max_dep_phase = max(max_dep_phase, _get_phase(dep) + 1)
        phase_of[sw] = max_dep_phase
        return max_dep_phase

    for sw in sorted_list:
        _get_phase(sw)

    # Group by phase
    max_phase = max(phase_of.values()) if phase_of else 0
    phases: list[dict] = []
    for phase_num in range(max_phase + 1):
        phase_tasks = []
        for sw in sorted_list:
            if phase_of[sw] == phase_num:
                version = _get_version(sw)
                status = check_task_status(sw, version)
                objective = generate_subtask_objective(sw, version, project_dir)
                phase_tasks.append({
                    "software": sw,
                    "version": version,
                    "status": status,
                    "objective": objective,
                })
        if phase_tasks:
            phases.append({
                "phase": phase_num,
                "tasks": phase_tasks,
            })

    # Step 3: Print plan
    _print_plan(phases)

    return phases


def _print_plan(phases: list[dict]) -> None:
    """Pretty-print the batch plan."""
    total = sum(len(p["tasks"]) for p in phases)
    already_done = sum(
        1 for p in phases for t in p["tasks"] if t["status"] == "finished"
    )
    to_build = total - already_done

    print(f"\n  📋 批量编译计划 ({total} 个软件, {to_build} 个待编译, {already_done} 个已完成)")
    print(f"  {'═' * 60}")

    for phase_info in phases:
        phase_num = phase_info["phase"]
        tasks = phase_info["tasks"]

        if phase_num == 0:
            phase_label = "基础库（无依赖，可并行）"
        else:
            deps_names = set()
            for t in tasks:
                deps_info = _KNOWN_DEPS.get(t["software"], {})
                for dep in deps_info.get("required", []):
                    deps_names.add(dep)
            phase_label = f"依赖 {', '.join(sorted(deps_names))}"

        print(f"\n  Phase {phase_num}: {phase_label}")
        print(f"  {'─' * 50}")

        for task in tasks:
            sw = task["software"]
            ver = task["version"]
            status = task["status"]
            icon = _STATUS_ICONS.get(status, "?")
            skip_note = " (跳过 — 已完成)" if status == "finished" else ""
            if status == "failed":
                skip_note = " (⚠️ 之前失败，需重试)"
            print(f"    {icon} {sw} {ver}{skip_note}")

    print(f"\n  {'═' * 60}")
    print(f"  共 {len(phases)} 个阶段, {to_build} 个子任务待创建")
    print()


# ═══════════════════════════════════════════════════════
# 6. Generate batch script
# ═══════════════════════════════════════════════════════

def generate_batch_script(software_list: list[str]) -> str:
    """生成主任务调度脚本（createSubTask 调用序列）。

    输出一段 createSubTask 调用序列，供主任务 AI 直接执行。

    Args:
        software_list: 软件名称列表。

    Returns:
        调度脚本文本。
    """
    project_dir = find_project_dir()

    phases = plan_batch(software_list)
    if not phases:
        return "# 无任务需要调度\n"

    lines = [
        "# ═══════════════════════════════════════════════════",
        "# 多任务编译调度脚本（由 dispatch 自动生成）",
        f"# 项目根目录: {project_dir}",
        "# ═══════════════════════════════════════════════════",
        "",
    ]

    for phase_info in phases:
        phase_num = phase_info["phase"]
        tasks = phase_info["tasks"]
        pending_tasks = [t for t in tasks if t["status"] != "finished"]

        if not pending_tasks:
            lines.append(f"# Phase {phase_num}: 全部已完成，跳过")
            lines.append("")
            continue

        if phase_num == 0:
            lines.append(f"# Phase {phase_num}: 基础库（无依赖，可并行）")
        else:
            lines.append(f"# Phase {phase_num}: 依赖前置阶段的软件")

        for task in pending_tasks:
            sw = task["software"]
            ver = task["version"]
            obj = task["objective"]

            if task["status"] == "failed":
                lines.append(f"# ⚠️ {sw} {ver} 之前失败，建议重试")

            lines.append(f'createSubTask(')
            lines.append(f'    title="编译 {sw} {ver}",')
            # Use a truncated hint in the call; the full objective is available
            lines.append(f'    objective="""{obj}""",')
            lines.append(f'    isAsync=True')
            lines.append(f')')
            lines.append("")

        lines.append(f"# waitSubTask for all Phase {phase_num} tasks")
        lines.append("")

    lines.append("# ═══════════════════════════════════════════════════")
    lines.append("# 全部完成后审计:")
    sw_ver_pairs = " ".join(
        f"{t['software']}" for p in phases for t in p["tasks"]
    )
    lines.append(
        f"# python3 $SKILL_ROOT/scripts/ohc-run.py dispatch status {sw_ver_pairs}"
    )
    lines.append("# ═══════════════════════════════════════════════════")

    script = "\n".join(lines)
    print(script)
    return script


# ═══════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════

def dispatch_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc dispatch"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="ohc dispatch",
        description="多任务编译调度 — 依赖排序、子任务生成、状态检查",
    )
    sub = parser.add_subparsers(dest="subcmd")

    # plan
    p_plan = sub.add_parser("plan", help="生成分阶段执行计划")
    p_plan.add_argument("software", nargs="+", help="软件名称列表")

    # status
    p_status = sub.add_parser("status", help="查看任务状态")
    p_status.add_argument("software", nargs="+", help="软件名称列表")

    # objective
    p_obj = sub.add_parser("objective", help="输出子任务 objective")
    p_obj.add_argument("software", help="软件名称")
    p_obj.add_argument("version", help="版本号")

    # script
    p_script = sub.add_parser("script", help="生成 createSubTask 调度脚本")
    p_script.add_argument("software", nargs="+", help="软件名称列表")

    args = parser.parse_args(argv)

    if not args.subcmd:
        parser.print_help()
        return 0

    if args.subcmd == "plan":
        phases = plan_batch(args.software)
        return 0 if phases else 1

    elif args.subcmd == "status":
        dispatch_status(args.software)
        return 0

    elif args.subcmd == "objective":
        project_dir = find_project_dir()
        obj = generate_subtask_objective(args.software, args.version, project_dir)
        print(obj)
        return 0

    elif args.subcmd == "script":
        script = generate_batch_script(args.software)
        return 0 if script else 1

    return 0
