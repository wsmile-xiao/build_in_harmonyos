"""HANDOFF protocol — structured handover from script to AI.

Unified HANDOFF output with JSON persistence. Creates
single standardized module that:

1. Outputs the HANDOFF block to stdout (backward compatible)
2. Persists to .handoff.json in the archive dir (new: cross-session recovery)
3. Updates .build-status.json in the project root (new: global status)
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

from .utils import find_project_dir


@dataclass
class HandoffData:
    """Structured HANDOFF block."""
    exit_reason: str          # configure_failed | make_failed | cmake_build_failed | ninja_build_failed
                              # | dependency_missing ⭐ 新增 | build_tool_missing ⭐ 新增
    exit_code: int            # 1=fatal, 2=resumable
    step_failed: str          # Step3 | Step4
    resume_cmd: str           # Full command to resume
    knowledge_hit: str        # E0xx or "none"
    knowledge_gap: bool       # True = no match found (gap in knowledge)
    log_file: str             # Path to build log
    src_dir: str              # Path to source directory
    task_card: str            # Path to TASK_CARD.md
    software_name: str        # e.g. "sed"
    software_version: str     # e.g. "4.9"
    archive_dir: str          # Path to archive directory
    ai_next_actions: list[str] = None  # List of actions for AI
    
    # ⭐ 新增字段：依赖缺失信息
    missing_dependency: str = ""       # 缺失的依赖名称（如 "openssl", "zlib"）
    missing_version: str = ""          # 所需版本（如 "1.1.1"）
    dependency_type: str = ""          # library | tool | command
    precompiled_available: bool = False  # cmd-pkgs 是否有预编译包

    def __post_init__(self):
        if self.ai_next_actions is None:
            self.ai_next_actions = []


# ═══════════════════════════════════════════════════════
# Stdout output (backward compatible with bash version)
# ═══════════════════════════════════════════════════════

def format_handoff_block(data: HandoffData) -> str:
    """Format the HANDOFF block for stdout (same visual format as bash)."""
    is_knowledge = data.exit_reason in ("finish_success", "finish_knowledge_required")
    is_dep_missing = data.exit_reason in ("dependency_missing", "build_tool_missing", "command_mismatch")

    if is_knowledge:
        is_blocking = data.exit_reason == "finish_knowledge_required"
        header = "KNOWLEDGE CONSOLIDATION — MANDATORY" if is_blocking else "KNOWLEDGE CONSOLIDATION"
        exit_hint = "⚠️ 阻塞！必须完成知识整理后重新 finish" if is_blocking else "知识整理已完成"
    elif is_dep_missing:
        header = "HANDOFF — ⭐ 依赖缺失"
        exit_hint = f"resumable（安装依赖后继续）"
    else:
        header = "HANDOFF"
        exit_hint = f"{'resumable' if data.exit_code == 2 else 'fatal'}"

    lines = [
        "",
        f"╔═══ {header} ══════════════════════════════════╗",
        f"║ EXIT_REASON: {data.exit_reason}",
        f"║ EXIT_CODE: {data.exit_code} ({exit_hint})",
        f"║ STEP_FAILED: {data.step_failed}",
        f"║ RESUME_CMD: {data.resume_cmd}",
    ]

    # ⭐ 新增：依赖缺失信息
    if is_dep_missing and data.missing_dependency:
        lines += [
            f"║ MISSING_DEPENDENCY: {data.missing_dependency}",
            f"║ MISSING_VERSION: {data.missing_version or 'any'}",
            f"║ DEPENDENCY_TYPE: {data.dependency_type}",
            f"║ PRECOMPILED_AVAILABLE: {'yes' if data.precompiled_available else 'no'}",
        ]

    if not is_knowledge and not is_dep_missing:
        lines += [
            f"║ KNOWLEDGE_HIT: {data.knowledge_hit}",
            f"║ KNOWLEDGE_GAP: {'true' if data.knowledge_gap else 'false'}",
            f"║ LOG_FILE: {data.log_file}",
            f"║ SRC_DIR: {data.src_dir}",
            f"║ TASK_CARD: {data.task_card}",
        ]

    lines += [
        f"║ SOFTWARE: {data.software_name} {data.software_version}",
        f"║ ARCHIVE_DIR: {data.archive_dir}",
        "║",
        "║ AI NEXT ACTIONS:",
    ]
    for action in data.ai_next_actions:
        lines.append(f"║   {action}")
    lines.append("╚══════════════════════════════════════════════╝")
    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Persistence
# ═══════════════════════════════════════════════════════

def _handoff_json_path(archive_dir: str) -> str:
    return os.path.join(archive_dir, ".handoff.json")


def _build_status_path(project_dir: str | None = None) -> str:
    pdir = project_dir or find_project_dir()
    return os.path.join(pdir, ".build-status.json")


def persist_handoff(data: HandoffData, project_dir: str | None = None) -> None:
    """Persist HANDOFF data to two files:

    1. {archive_dir}/.handoff.json — per-build handoff state
    2. {project_dir}/.build-status.json — global build status registry
    """
    now = datetime.now(timezone.utc).isoformat()

    # 1. Per-build .handoff.json
    handoff_path = _handoff_json_path(data.archive_dir)
    os.makedirs(os.path.dirname(handoff_path), exist_ok=True)
    handoff_dict = {
        "timestamp": now,
        "software": data.software_name,
        "version": data.software_version,
        "exit_reason": data.exit_reason,
        "exit_code": data.exit_code,
        "step_failed": data.step_failed,
        "resume_cmd": data.resume_cmd,
        "knowledge_hit": data.knowledge_hit,
        "knowledge_gap": data.knowledge_gap,
        "log_file": data.log_file,
        "src_dir": data.src_dir,
        "task_card": data.task_card,
        "ai_next_actions": data.ai_next_actions,
        # ⭐ 新增字段
        "missing_dependency": data.missing_dependency,
        "missing_version": data.missing_version,
        "dependency_type": data.dependency_type,
        "precompiled_available": data.precompiled_available,
    }
    with open(handoff_path, "w", encoding="utf-8") as f:
        json.dump(handoff_dict, f, ensure_ascii=False, indent=2)

    # 2. Global .build-status.json
    status_path = _build_status_path(project_dir)
    status = _load_build_status(status_path)

    status_key = f"{data.software_name}/{data.software_version}"
    status[status_key] = {
        "software": data.software_name,
        "version": data.software_version,
        "status": "failed" if data.exit_code == 1 else "paused",
        "step_failed": data.step_failed,
        "exit_reason": data.exit_reason,
        "knowledge_hit": data.knowledge_hit,
        "knowledge_gap": data.knowledge_gap,
        "archive_dir": data.archive_dir,
        "resume_cmd": data.resume_cmd,
        "log_file": data.log_file,
        "task_card": data.task_card,
        "timestamp": now,
        # ⭐ 新增字段
        "missing_dependency": data.missing_dependency,
        "precompiled_available": data.precompiled_available,
    }

    _save_status_locked(status_path, status)


def update_build_status(
    software: str,
    version: str,
    new_status: str,
    project_dir: str | None = None,
    **extra_fields,
) -> None:
    """Update global build status (e.g. mark as 'completed' or 'running')."""
    status_path = _build_status_path(project_dir)
    status = _load_build_status(status_path)
    status_key = f"{software}/{version}"
    now = datetime.now(timezone.utc).isoformat()

    if status_key not in status:
        status[status_key] = {
            "software": software,
            "version": version,
            "status": new_status,
            "timestamp": now,
        }
    else:
        status[status_key]["status"] = new_status
        status[status_key]["timestamp"] = now

    status[status_key].update(extra_fields)

    _save_status_locked(status_path, status)

    # If completed, clean up the per-build .handoff.json
    if new_status in ("completed", "published"):
        archive_dir = status[status_key].get("archive_dir", "")
        if archive_dir:
            hp = _handoff_json_path(archive_dir)
            if os.path.isfile(hp):
                os.rename(hp, hp + ".resolved")


def _save_status_locked(status_path: str, status: dict, mutator=None) -> None:
    """v12.6: 事务式独占锁——读-改-写全程在锁内（修 P1 并发互覆盖）。

    mutator(status)->None 时，锁内重读最新状态再变更，避免覆盖他进程更新。
    """
    import fcntl
    lock_path = status_path + ".lock"
    with open(lock_path, "w", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            if mutator is not None:
                status = _load_build_status(status_path)
                mutator(status)
            tmp = status_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            os.replace(tmp, status_path)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _load_build_status(path: str) -> dict:
    """Load .build-status.json, return empty dict if not found."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ═══════════════════════════════════════════════════════
# Public API: emit HANDOFF (stdout + persist)
# ═══════════════════════════════════════════════════════

def emit_handoff(data: HandoffData, project_dir: str | None = None) -> None:
    """Emit HANDOFF: print to stdout AND persist to disk."""
    # stdout (backward compatible)
    print(format_handoff_block(data), file=sys.stdout)

    # Persist to disk (new)
    try:
        persist_handoff(data, project_dir)
    except Exception as e:
        print(f"  ⚠️  HANDOFF 持久化失败: {e}", file=sys.stderr)


# ═══════════════════════════════════════════════════════
# CLI entry
# ═══════════════════════════════════════════════════════

def handoff_cli(argv: list[str] | None = None) -> int:
    """CLI for: python3 -m ohc handoff <json_data>

    Reads HandoffData fields from a JSON string on stdin or as first argument.
    Called internally to emit HANDOFF output.
    """
    import argparse
    parser = argparse.ArgumentParser(prog="ohc handoff", description="Emit HANDOFF block")
    parser.add_argument("json_data", nargs="?", help="HandoffData as JSON string")
    parser.add_argument("--file", help="Read JSON from file")
    parser.add_argument("--project-dir", help="Project root directory")

    args = parser.parse_args(argv)

    raw_json = args.json_data
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw_json = f.read()
    elif not raw_json:
        raw_json = sys.stdin.read()

    if not raw_json.strip():
        print("❌ No JSON data provided", file=sys.stderr)
        return 1

    try:
        d = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 1

    data = HandoffData(
        exit_reason=d.get("exit_reason", "unknown"),
        exit_code=d.get("exit_code", 2),
        step_failed=d.get("step_failed", ""),
        resume_cmd=d.get("resume_cmd", ""),
        knowledge_hit=d.get("knowledge_hit", "none"),
        knowledge_gap=d.get("knowledge_gap", True),
        log_file=d.get("log_file", ""),
        src_dir=d.get("src_dir", ""),
        task_card=d.get("task_card", ""),
        software_name=d.get("software_name", ""),
        software_version=d.get("software_version", ""),
        archive_dir=d.get("archive_dir", ""),
        ai_next_actions=d.get("ai_next_actions", []),
    )

    emit_handoff(data, project_dir=args.project_dir)
    return 0
