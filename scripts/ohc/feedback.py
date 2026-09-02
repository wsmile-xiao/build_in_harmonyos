"""SKILL_FEEDBACK — 流程终态反馈生成。

在 SKILL 整个流程结束后，自动收集全流程数据，生成结构化反馈报告。
报告写入 feedback/SKILL_FEEDBACK_{random}.md，包含：
- 背景：软件信息、构建配置
- 情况：执行概要、失败分析、知识图谱、AI检视、CI、效率
- 建议：AI 填写的改进建议（(请填写) 占位符，HANDOFF 强制）
- 作者：从 git config 获取

Usage:
    python3 ohc-run.py feedback <software> <version>
    python3 ohc-run.py feedback <software> <version> --resume
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .utils import (
    find_executable,
    find_project_dir,
    get_agent_id,
    graph_dir,
    log_info,
    log_ok,
    log_warn,
    log_fail,
)

_GIT = find_executable("git")


def _archive_dir(letter: str, name: str, version: str,
                 pdir: str | None = None) -> Path:
    return Path(pdir or find_project_dir()) / "archives" / letter / name / version


def _parse_yaml_simple(path: Path) -> dict:
    """Simple flat YAML parser (key: value, with list support)."""
    data: dict = {}
    if not path.exists():
        return data
    current_list_key: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if line.startswith(" ") or line.startswith("\t"):
            stripped = line.strip()
            if stripped.startswith("- ") and current_list_key:
                item = stripped[2:].strip()
                if (item.startswith('"') and item.endswith('"')) or \
                   (item.startswith("'") and item.endswith("'")):
                    item = item[1:-1]
                data.setdefault(current_list_key, []).append(item)
            continue
        current_list_key = None
        if ": " in stripped or stripped.endswith(":"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val:
                data[key] = val
            else:
                current_list_key = key
                data.setdefault(key, [])
    return data


# ═══════════════════════════════════════════════════════
# State management
# ═══════════════════════════════════════════════════════

def _state_path(ver_dir: Path) -> Path:
    """v12.10.1: 状态文件路径——顶层 .ohc/，永不出现在 archives/ 树内。

    事故：v12.10 把 .feedback-state.json 写进 archives/<l>/<sw>/<ver>/ 且
    未 gitignore → bot 提交进 PR → JC5 未登记隐藏文件拦截（lua-mimetypes）。
    修复：迁至 <root>/.ohc/feedback-state/<l>/<sw>/<ver>.json——JC5 只扫
    archives/，且 .gitignore 已加 .ohc/ 双保险。
    """
    try:
        root = ver_dir.parents[3]  # archives/<l>/<sw>/<ver> → 项目根
        rel = ver_dir.relative_to(root)
        if len(rel.parts) == 4 and rel.parts[0] == "archives":
            p = (root / ".ohc" / "feedback-state" / rel.parts[1]
                 / rel.parts[2] / (rel.parts[3] + ".json"))
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    except Exception:
        pass
    return ver_dir / ".feedback-state.json"  # 结构异常时兜底


def _load_feedback_state(ver_dir: Path) -> dict:
    """Load feedback state from .ohc/ (v12.10.1; 自动迁移 archives 内遗留副本)."""
    state_path = _state_path(ver_dir)
    legacy = ver_dir / ".feedback-state.json"
    if not state_path.exists() and legacy.exists():
        # v12.10 遗留位置迁移：读出→写入新位置→删旧文件（清出 archives 树）
        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        try:
            _save_feedback_state(ver_dir, data)
            legacy.unlink()
        except OSError:
            pass
    if not state_path.exists():
        return {}
    # v12.19a: 读侧瞬态重试——Windows 上写者 replace 窗口内读者可能拿到
    # PermissionError；读空/坏 JSON 时短退避重读一次，避免把瞬态当空状态
    # 返回（空状态会被上层回写 → 时间线全丢）
    for attempt in range(2):
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            if attempt == 0:
                time.sleep(0.03)
    return {}


def _save_feedback_state(ver_dir: Path, state: dict) -> None:
    """Save feedback state to .ohc/ (永不写进 archives/ - JC5 安全).

    v12.19: 原子写（tmp + os.replace）——半写状态被并发读者读到即
    JSONDecodeError → 静默当作空状态重写 → 时间线全丢。
    """
    state["last_updated"] = datetime.now().isoformat()
    p = _state_path(ver_dir)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8")
    # v12.19a: Windows 上目标文件被并发读者打开时 os.replace 抛
    # PermissionError（实测高频）——瞬时竞争，短退避重试必成；重试
    # 尽仍失败则直写兜底（罕见竞态下接受非原子，好过丢整条时间线）
    for i in range(4):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i < 3:
                time.sleep(0.02 * (i + 1))
    try:
        p.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8")
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


@contextmanager
def _state_lock(ver_dir: Path, timeout_s: float = 10.0,
                stale_s: float = 30.0):
    """v12.19: feedback 状态跨进程互斥（O_EXCL 自旋 + stale 接管）。

    竞态场景：budget-check 与 submit 两进程同时 record_event——
    读-改-写交错后，后写者用旧快照覆盖前写者 → 丢事件（task_started
    丢失会误判计时起点）。锁拿不到时降级（yield False），调用方走
    CAS 合并写兜底。正常持锁毫秒级；stale_s 后视为崩溃遗留强制接管。
    """
    lock_path = _state_path(ver_dir).with_suffix(".lock")
    acquired = False
    deadline = time.monotonic() + timeout_s
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        while not acquired:
            try:
                fd = os.open(str(lock_path),
                             os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                acquired = True
            except FileExistsError:
                try:
                    if time.time() - lock_path.stat().st_mtime > stale_s:
                        lock_path.unlink()
                        continue
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    break  # 降级：调用方走 CAS 合并写
                time.sleep(0.05)
            except OSError:
                break  # 文件系统异常（只读等）→ 降级
        yield acquired
    finally:
        if acquired:
            try:
                lock_path.unlink()
            except OSError:
                pass


# ═══════════════════════════════════════════════════════
# Data collection
# ═══════════════════════════════════════════════════════

def _get_git_author(project_dir: str) -> tuple[str, str]:
    """Get git user name and email."""
    name = ""
    email = ""
    try:
        result = subprocess.run(
            [_GIT, "config", "user.name"],
            cwd=project_dir, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            name = result.stdout.strip()
    except Exception:
        pass
    try:
        result = subprocess.run(
            [_GIT, "config", "user.email"],
            cwd=project_dir, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            email = result.stdout.strip()
    except Exception:
        pass
    return name or "unknown", email or "unknown"


def _get_git_commit(project_dir: str) -> str:
    """Get current git commit hash (short)."""
    try:
        result = subprocess.run(
            [_GIT, "rev-parse", "--short", "HEAD"],
            cwd=project_dir, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _generate_feedback_id(feedback_dir: Path) -> str:
    """Generate a unique random ID for the feedback file.

    Uses secrets.token_hex(4) for 8 hex chars, checks for collisions.
    """
    while True:
        hex_id = secrets.token_hex(4)
        candidate = feedback_dir / f"SKILL_FEEDBACK_{hex_id}.md"
        if not candidate.exists():
            return hex_id


def _collect_background(ver_dir: Path, software: str, version: str) -> dict:
    """Collect background data from manifest, conandata, conanfile, patches."""
    manifest = _parse_yaml_simple(ver_dir / "manifest.yaml")

    # Source URL from conandata.yml
    conandata = ver_dir / "conandata.yml"
    upstream_url = ""
    if conandata.exists():
        for line in conandata.read_text(encoding="utf-8", errors="replace").split("\n"):
            line = line.strip()
            if line.startswith("url:"):
                upstream_url = line.split(":", 1)[1].strip().strip('"').strip("'")
                break
    if not upstream_url:
        upstream_url = str(manifest.get("upstream_url", manifest.get("url", "")))

    # Dependencies from conanfile.py
    conanfile = ver_dir / "conanfile.py"
    deps: list[str] = []
    if conanfile.exists():
        content = conanfile.read_text(encoding="utf-8", errors="replace")
        deps = re.findall(r'self\.requires\(\s*["\']([^"\']+)["\']', content)
    # Also from manifest
    manifest_deps = manifest.get("dependencies", [])
    if isinstance(manifest_deps, list):
        for d in manifest_deps:
            if d not in deps:
                deps.append(d)

    # Patches
    patches_dir = ver_dir / "patches"
    patch_count = 0
    if patches_dir.is_dir():
        patch_count = len(list(patches_dir.glob("*.patch")))

    # Build system
    build_system = str(manifest.get("build_system", "unknown"))
    build_date = str(manifest.get("build_date", "unknown"))
    status = str(manifest.get("status", "unknown"))

    # Adaptation path
    adaptation_path = "路径 A（基础适配）" if patch_count > 0 else "路径 A（基础适配，无补丁）"

    # Build status text
    if status in ("published", "built"):
        build_status = "成功"
    else:
        build_status = "失败"

    # Dependencies display
    dep_str = "\n".join(f"- {d}" for d in deps) if deps else "无"

    return {
        "software": software,
        "version": version,
        "build_date": build_date,
        "build_system": build_system,
        "upstream_url": upstream_url or "(未知)",
        "adaptation_path": adaptation_path,
        "patch_count": str(patch_count),
        "dependencies": dep_str,
        "build_status": build_status,
    }


def _collect_situation(ver_dir: Path, project_dir: str) -> dict:
    """Collect situation data from CI result, submit state, notes, test report."""
    result = {}

    # ── Local CI (W3) ──
    ci_result_path = ver_dir / ".ci-result.json"
    local_ci = "未知"
    if ci_result_path.exists():
        try:
            ci_data = json.loads(ci_result_path.read_text(encoding="utf-8"))
            local_ci = "通过" if ci_data.get("exit_code") == 0 else f"失败 (exit_code={ci_data.get('exit_code')})"
        except (json.JSONDecodeError, OSError):
            local_ci = "解析失败"
    result["local_ci_result"] = local_ci

    # ── Submit state (AI Review + PR) ──
    state_path = ver_dir / ".submit-state.json"
    pr_number = "—"
    review_phase = "—"
    remote_ci = "未知"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            pr_number = str(state.get("pr_number", "—"))
            review_phase = str(state.get("review_phase", "—"))
            result["branch_name"] = state.get("branch_name", "")
        except (json.JSONDecodeError, OSError):
            pass
    result["pr_number"] = pr_number
    result["ai_review_phase"] = review_phase
    # Remote CI: since feedback is generated after submit success, CI passed
    if pr_number != "—":
        remote_ci = "通过 (PR 校验)"
    result["remote_ci_result"] = remote_ci
    result["ci_failure_reason"] = "无"

    # ── AI Review details ──
    phase_map = {
        "1": "Phase 1 (等待摘要)",
        "2": "Phase 2 (评估摘要)",
        "3": "Phase 3 (等待检视意见)",
        "4": "Phase 4 (处理检视意见)",
        "5": "Phase 5 (完成)",
    }
    result["ai_review_phase_desc"] = phase_map.get(review_phase, review_phase)
    result["summary_evaluation"] = "(请填写)"
    result["review_opinion_count"] = "(请填写)"
    result["opinion_handling"] = "(请填写)"

    # ── Knowledge graph ──
    manifest = _parse_yaml_simple(ver_dir / "manifest.yaml")
    knowledge_ref = manifest.get("knowledge_ref", [])
    if isinstance(knowledge_ref, list):
        result["knowledge_ref"] = ", ".join(knowledge_ref) if knowledge_ref else "无"
    else:
        result["knowledge_ref"] = str(knowledge_ref) or "无"

    knowledge_gained = manifest.get("knowledge_gained", [])
    if isinstance(knowledge_gained, list):
        result["knowledge_drafts"] = f"{len(knowledge_gained)} 条" if knowledge_gained else "无"
    else:
        result["knowledge_drafts"] = "无"

    # Draft count in knowledge/drafts/
    draft_dir = Path(project_dir) / "knowledge" / "drafts"
    draft_count = 0
    if draft_dir.is_dir():
        draft_count = len(list(draft_dir.glob("*.kv")))
    result["engine_hits"] = f"草稿目录 {draft_count} 条" if draft_count else "无草稿"
    result["uncovered_patterns"] = "(请填写)"

    # ── Issues from notes.md ──
    notes_path = ver_dir / "notes.md"
    issues: list[str] = []
    if notes_path.exists():
        content = notes_path.read_text(encoding="utf-8", errors="replace")
        in_issues = False
        for line in content.split("\n"):
            if "问题" in line and "解决方案" in line:
                in_issues = True
                continue
            if in_issues:
                if line.startswith("## "):
                    in_issues = False
                    continue
                if line.startswith("|") and "---" not in line and "#" not in line:
                    cols = [c.strip() for c in line.split("|")]
                    if len(cols) >= 4 and cols[1] and cols[1] != "#":
                        issues.append(f"- **{cols[1]}**: 根因={cols[2]}, 解决方案={cols[3]}")
    result["failures_and_issues"] = "\n".join(issues) if issues else "本次流程未遇到阻塞性问题"

    # ── Test summary ──
    test_report = ver_dir / "reports" / "test-report.md"
    test_total = 0
    test_passed = 0
    test_failed = 0
    test_skipped = 0
    if test_report.exists():
        content = test_report.read_text(encoding="utf-8", errors="replace")
        for line in content.split("\n"):
            stripped = line.strip()
            if "总测试数" in stripped:
                m = re.search(r'\|\s*(\d+)\s', stripped)
                if m:
                    test_total = int(m.group(1))
            elif "通过" in stripped and "PASS" in stripped:
                m = re.search(r'\|\s*(\d+)\s', stripped)
                if m:
                    test_passed = int(m.group(1))
            elif "失败" in stripped and "FAIL" in stripped:
                m = re.search(r'\|\s*(\d+)\s', stripped)
                if m:
                    test_failed = int(m.group(1))
            elif "跳过" in stripped and "SKIP" in stripped:
                m = re.search(r'\|\s*(\d+)\s', stripped)
                if m:
                    test_skipped = int(m.group(1))
    result["test_summary"] = f"总计 {test_total}, 通过 {test_passed}, 失败 {test_failed}, 跳过 {test_skipped}"

    # ── Execution summary ──
    status = str(manifest.get("status", "unknown"))
    init_result = "完成" if ver_dir.exists() else "未完成"
    build_result = "成功" if status in ("published", "built") else "失败"
    verify_result = "(请填写)"
    finish_result = "完成" if (ver_dir / "manifest.yaml").exists() else "未完成"
    submit_result = f"PR #{pr_number}, CI 通过" if pr_number != "—" else "(请填写)"

    result["execution_table"] = (
        f"| init-build | 源码下载/解压 | {init_result} | |\n"
        f"| build | 编译构建 | {build_result} | 构建系统: {manifest.get('build_system', 'unknown')} |\n"
        f"| conan-verify | 配方验证 | {verify_result} | |\n"
        f"| finish | 归档收尾 | {finish_result} | |\n"
        f"| submit | PR提交+AI检视+CI | {submit_result} | AI Review: {result['ai_review_phase_desc']} |"
    )

    # ── Efficiency ──
    result["handoff_count"] = "(请填写)"
    result["retry_count"] = "(请填写)"
    result["bottlenecks"] = "(请填写)"
    result["slow_steps"] = "(请填写)"

    return result


# ═══════════════════════════════════════════════════════
# HANDOFF
# ═══════════════════════════════════════════════════════

def _emit_feedback_handoff(software: str, version: str, ver_dir: Path,
                           project_dir: str, reason: str,
                           actions: list[str]) -> None:
    """Emit HANDOFF block for feedback phase."""
    from .handoff import HandoffData, emit_handoff
    resume_cmd = f"python3 scripts/ohc-run.py feedback {software} {version} --resume"
    data = HandoffData(
        exit_reason=reason,
        exit_code=2,
        step_failed="feedback",
        resume_cmd=resume_cmd,
        knowledge_hit="none",
        knowledge_gap=False,
        log_file="",
        src_dir="",
        task_card="",
        software_name=software,
        software_version=version,
        archive_dir=str(ver_dir),
        ai_next_actions=actions,
    )
    emit_handoff(data, project_dir=project_dir)


# ═══════════════════════════════════════════════════════
# Template rendering
# ═══════════════════════════════════════════════════════

def _render_feedback_body(bg: dict, sit: dict, author_name: str,
                          author_email: str, agent_id: str,
                          timestamp: str, git_commit: str,
                          feedback_id: str,
                          events: list | None = None) -> str:
    """Render the feedback report body from collected data."""
    events_section = _render_events_section(events or [])
    return f"""# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_{feedback_id}.md`

---

## 背景

- **软件名称**: {bg['software']}
- **版本**: {bg['version']}
- **构建日期**: {bg['build_date']}
- **构建系统**: {bg['build_system']}
- **上游仓库**: {bg['upstream_url']}
- **适配路径**: {bg['adaptation_path']}
- **补丁数量**: {bg['patch_count']}
- **编译依赖**:
{bg['dependencies']}
- **最终状态**: {bg['build_status']}

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
{sit['execution_table']}

### 失败与问题

{sit['failures_and_issues']}

### 知识图谱使用情况

- **引用知识条目**: {sit['knowledge_ref']}
- **新增知识草稿**: {sit['knowledge_drafts']}
- **引擎命中情况**: {sit['engine_hits']}
- **测试统计**: {sit['test_summary']}
- **未覆盖的错误模式**: {sit['uncovered_patterns']}

### AI 检视结果

- **检视阶段到达**: {sit['ai_review_phase_desc']}
- **变更摘要评估**: {sit['summary_evaluation']}
- **检视意见数量**: {sit['review_opinion_count']}
- **检视意见处理**: {sit['opinion_handling']}

### CI 结果

- **本地 CI 模拟 (W3)**: {sit['local_ci_result']}
- **远程 CI (PR 校验)**: {sit['remote_ci_result']}
- **CI 失败原因**: {sit['ci_failure_reason']}

### 效率分析

- **HANDOFF 次数**: {sit['handoff_count']}
- **重试次数**: {sit['retry_count']}
- **关键瓶颈**: {sit['bottlenecks']}
- **耗时较长的步骤**: {sit['slow_steps']}
{events_section}
---

## 建议

### SKILL 设计改进

(请填写)

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

(请填写)

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

(请填写)

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

(请填写)

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: {author_name}
- **邮箱**: {author_email}
- **Agent ID**: {agent_id}
- **生成时间**: {timestamp}
- **PR 编号**: {sit['pr_number']}
- **Git Commit**: {git_commit}
"""


def _count_placeholders(text: str) -> int:
    """Count (请填写) placeholders in text."""
    return text.count("(请填写)")


# ═══════════════════════════════════════════════════════
# v12.10: 骨架前置 / 事件累积 / 状态查询（防丢失协议）
#
# 背景：旧流程 feedback 在 CI 绿后最后一步才生成，且只写本地不入仓——
# agent 在此之前死亡即永久丢失，失败分支更是从不生成（幸存者偏差）。
# 协议（对齐 R42 先落盘模式）：
#   1. PR 创建瞬间生成骨架（ensure_feedback_skeleton）
#   2. 全流程事件累积进 .feedback-state.json（record_event，单一咽喉挂接）
#   3. result 终态时计算 feedback_pending 并兜底补骨架（feedback_pending_flag）
#   4. 反馈完整后由 submit 终局自动 commit+push 入任务分支
# ═══════════════════════════════════════════════════════

_EVENTS_BEGIN = "<!-- EVENTS:BEGIN -->"
_EVENTS_END = "<!-- EVENTS:END -->"
_SUGGESTION_FIELDS = ["SKILL 设计改进", "模板改进", "自动化补全", "知识图谱覆盖"]


def record_event(ver_dir, event: str, detail: str = "") -> None:
    """经验事件累积（v12.10）：失败/重试/HANDOFF 经验不随工作区回收丢失。

    尽力而为：任何异常静默吞掉，绝不阻塞主流程。
    """
    try:
        if ver_dir is None or not Path(ver_dir).exists():
            return
        # v12.19: 读-改-写整体进锁（跨进程互斥）；锁超时降级时走 CAS
        # 合并写——写前复查事件数，他者已写则重读合并，把覆盖窗口从
        # 整个持锁周期缩到两条指令之间（丢事件概率再降数量级）
        vd = Path(ver_dir)
        with _state_lock(vd) as locked:
            state = _load_feedback_state(vd)
            events = state.get("events") or []
            base = len(events)
            entry = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": str(event)[:60],
                "detail": (detail or "")[:300],
            }
            if not locked:
                cur = _load_feedback_state(vd)
                cur_events = cur.get("events") or []
                if len(cur_events) != base:
                    events = cur_events        # 他者已写 → 合并到最新
                    base = len(events)
            events = events + [entry]
            state["events"] = events
            _save_feedback_state(vd, state)
    except Exception:
        pass


def _render_events_section(events: list) -> str:
    """渲染自动事件时间线（无占位符，纯自动数据）。"""
    if not events:
        return ""
    n_handoff = sum(1 for e in events
                    if str(e.get("event", "")).startswith("handoff:"))
    n_retry = sum(1 for e in events
                  if any(k in str(e.get("event", ""))
                         for k in ("retry", "push", "resume", "pr_created")))
    lines = [
        _EVENTS_BEGIN,
        "### 过程事件时间线（自动记录，v12.10）",
        "",
        f"共 {len(events)} 个事件"
        f"（含 {n_handoff} 次 HANDOFF、{n_retry} 次推进/恢复），"
        "由 harness 各闸门自动累积：",
        "",
        "| 时间 | 事件 | 详情 |",
        "|------|------|------|",
    ]
    for e in events[-30:]:
        detail = (str(e.get("detail", ""))
                  .replace("|", "\\|").replace("\n", " "))
        lines.append(f"| {e.get('ts', '')} | {e.get('event', '')} | {detail} |")
    lines.append(_EVENTS_END)
    return "\n".join(lines) + "\n"


def _refresh_events_section(feedback_path: Path, ver_dir: Path) -> None:
    """把 state 中累积的最新事件刷进报告（幂等：标记块整体替换）。"""
    try:
        state = _load_feedback_state(ver_dir)
        section = _render_events_section(state.get("events") or [])
        if not section:
            return
        body = feedback_path.read_text(encoding="utf-8")
        if _EVENTS_BEGIN in body and _EVENTS_END in body:
            pre = body.split(_EVENTS_BEGIN)[0]
            post = body.split(_EVENTS_END, 1)[1].lstrip("\n")
            body = pre + section + post
        elif "\n---\n\n## 建议\n" in body:
            body = body.replace("\n---\n\n## 建议\n",
                                "\n" + section + "\n---\n\n## 建议\n", 1)
        else:
            return
        feedback_path.write_text(body, encoding="utf-8")
    except Exception:
        pass


def _generate_report(ver_dir: Path, project_dir: str, software: str,
                     version: str) -> tuple[Path, str, int]:
    """渲染并落盘反馈报告（骨架/终稿共用，v12.10 抽取）。

    复用 state 中已有 feedback_id——骨架与终稿同一文件，避免孤儿文件。
    返回 (path, feedback_id, 剩余占位符数)。
    """
    bg = _collect_background(ver_dir, software, version)
    sit = _collect_situation(ver_dir, project_dir)
    author_name, author_email = _get_git_author(project_dir)
    git_commit = _get_git_commit(project_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    agent_id = get_agent_id(project_dir)
    feedback_dir = Path(project_dir) / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    state = _load_feedback_state(ver_dir)
    feedback_id = state.get("feedback_id") or _generate_feedback_id(feedback_dir)
    feedback_path = feedback_dir / f"SKILL_FEEDBACK_{feedback_id}.md"
    body = _render_feedback_body(
        bg, sit, author_name, author_email,
        agent_id, timestamp, git_commit, feedback_id,
        events=state.get("events") or [])
    feedback_path.write_text(body, encoding="utf-8")
    _save_feedback_state(ver_dir, {**state,
                                   "feedback_id": feedback_id,
                                   "feedback_path": str(feedback_path),
                                   "status": "draft",
                                   "created_at": timestamp})
    remaining = sum(1 for f in _SUGGESTION_FIELDS
                    if f"{f}\n\n(请填写)" in body or _placeholder_in(body, f))
    return feedback_path, feedback_id, remaining


def _placeholder_in(body: str, field: str) -> bool:
    """字段小节内是否仍有 (请填写)。"""
    m = re.search(rf"### {re.escape(field)}\n(.*?)(?=\n### |\n## |\Z)",
                  body, re.S)
    return bool(m and "(请填写)" in m.group(1))


def ensure_feedback_skeleton(software: str, version: str,
                             pdir: str | None = None,
                             reason: str = "pr_created") -> Path | None:
    """R42 同款先落盘（v12.10）：PR 创建瞬间即生成 feedback 骨架。

    已存在（state 有 id 且文件在）则只追加事件不重复生成，幂等。
    终稿由 cmd_feedback 接管（AI 填建议 → --resume 闭环）。
    """
    try:
        project_dir = pdir or find_project_dir()
        letter = software[0].lower()
        ver_dir = _archive_dir(letter, software, version, project_dir)
        if not ver_dir.exists():
            return None
        state = _load_feedback_state(ver_dir)
        fid = state.get("feedback_id")
        if fid:
            fpath = Path(project_dir) / "feedback" / f"SKILL_FEEDBACK_{fid}.md"
            if fpath.exists():
                record_event(ver_dir, "skeleton_exists", reason)
                return fpath
        path, _fid, _n = _generate_report(ver_dir, project_dir,
                                          software, version)
        record_event(ver_dir, "skeleton_created", reason)
        return path
    except Exception:
        return None


def feedback_status(software: str, version: str,
                    pdir: str | None = None) -> dict:
    """查询 feedback 状态（v12.10，供 result 兜底与 ECS 收割判断）。"""
    out = {"exists": False, "complete": False, "path": "", "feedback_id": "",
           "pending": True}
    try:
        project_dir = pdir or find_project_dir()
        letter = software[0].lower()
        ver_dir = _archive_dir(letter, software, version, project_dir)
        state = _load_feedback_state(ver_dir)
        fid = state.get("feedback_id", "")
        if fid:
            fpath = (Path(project_dir) / "feedback"
                     / f"SKILL_FEEDBACK_{fid}.md")
            if fpath.exists():
                complete = state.get("status") == "complete"
                out.update(exists=True, complete=complete,
                           path=str(fpath), feedback_id=fid,
                           pending=not complete)
    except Exception:
        pass
    return out


def feedback_pending_flag(software: str, version: str,
                          pdir: str | None = None,
                          skeleton_reason: str = "") -> bool:
    """result 终态兜底（v12.10）：缺失即补骨架，返回 pending 标志。

    供 result_report 在写 result.json 前调用——即使 agent 即将死亡，
    feedback_pending 字段也让 ECS 知道工作区还有未收割的反馈。
    """
    try:
        st = feedback_status(software, version, pdir=pdir)
        if st["complete"]:
            return False
        if not st["exists"]:
            ensure_feedback_skeleton(
                software, version, pdir=pdir,
                reason=skeleton_reason or "result_fallback")
        return True
    except Exception:
        return True


# ═══════════════════════════════════════════════════════
# Main command
# ═══════════════════════════════════════════════════════

def cmd_feedback(software: str, version: str,
                 pdir: str | None = None,
                 resume: bool = False) -> int:
    """Generate SKILL_FEEDBACK report at the end of the SKILL flow.

    On first run: collects data, generates report, emits HANDOFF if
    (请填写) placeholders remain for AI to fill in suggestions.
    On --resume: checks existing report completeness.

    Returns:
        0 — report complete (or generated with no placeholders)
        1 — HANDOFF emitted (AI must fill in suggestions)
    """
    project_dir = pdir or find_project_dir()
    agent_id = get_agent_id(project_dir)
    letter = software[0].lower()
    ver_dir = _archive_dir(letter, software, version, project_dir)
    feedback_dir = Path(project_dir) / "feedback"

    if not ver_dir.exists():
        log_fail(f"❌ 版本目录不存在: {ver_dir}")
        return 1

    # ── Resume: check existing report completeness ──
    if resume:
        state = _load_feedback_state(ver_dir)
        feedback_id = state.get("feedback_id")
        if not feedback_id:
            log_fail("❌ --resume 但状态文件中无 feedback_id")
            _emit_feedback_handoff(software, version, ver_dir, project_dir,
                "feedback_resume_no_state",
                ["状态文件 .feedback-state.json 中无 feedback_id",
                 f"请重新生成: python3 scripts/ohc-run.py feedback {software} {version}"])
            return 1

        feedback_path = feedback_dir / f"SKILL_FEEDBACK_{feedback_id}.md"
        if not feedback_path.exists():
            log_fail(f"❌ 反馈报告文件不存在: {feedback_path}")
            _emit_feedback_handoff(software, version, ver_dir, project_dir,
                "feedback_file_missing",
                [f"反馈报告文件不存在: {feedback_path}",
                 f"请重新生成: python3 scripts/ohc-run.py feedback {software} {version}"])
            return 1

        # v12.10: 恢复前先刷新事件时间线（骨架期之后累积的事件入报告）
        _refresh_events_section(feedback_path, ver_dir)
        content = feedback_path.read_text(encoding="utf-8")
        placeholder_count = _count_placeholders(content)
        if placeholder_count > 0:
            log_fail(f"❌ 反馈报告仍有 {placeholder_count} 处 (请填写) 未填充")
            _emit_feedback_handoff(software, version, ver_dir, project_dir,
                "feedback_incomplete",
                [f"反馈报告 {feedback_path.name} 有 {placeholder_count} 处 (请填写) 未填充",
                 f"请编辑 {feedback_path} 补充以下内容：",
                 "  - 建议 > SKILL 设计改进",
                 "  - 建议 > 模板改进",
                 "  - 建议 > 自动化补全",
                 "  - 建议 > 知识图谱覆盖",
                 "  - 情况 > 效率分析 (HANDOFF次数/重试次数/瓶颈/耗时)",
                 "  - 情况 > AI 检视结果 (摘要评估/意见数量/处理方式)",
                 "  - 情况 > 未覆盖的错误模式",
                 f"填充后: python3 scripts/ohc-run.py feedback {software} {version} --resume"])
            return 1

        log_ok(f"  ✅ SKILL_FEEDBACK 报告完整 ({feedback_path.name})")
        # v12.10: 终稿闭环，状态落 complete（供 feedback_status / ECS 收割判断）
        record_event(ver_dir, "feedback_complete_resume")
        _save_feedback_state(ver_dir, {**state, "status": "complete",
                                       "completed_at": datetime.now().isoformat(timespec="seconds")})
        print(f"\n  📋 SKILL_FEEDBACK 完成:")
        print(f"     文件: {feedback_path}")
        print(f"     ID: {feedback_id}")
        print(f"     状态: ✅ 完整 (0 处待填写)")
        return 0

    # ── First run: generate report ──
    # v12.10: 若骨架已由 submit 阶段前置生成（state 有 id 且文件在），
    # 视为"初稿已就位"，直接走完整性校验，不再另生成孤儿文件。
    state = _load_feedback_state(ver_dir)
    skeleton_id = state.get("feedback_id")
    skeleton_path = (feedback_dir / f"SKILL_FEEDBACK_{skeleton_id}.md"
                     if skeleton_id else None)
    if skeleton_path and skeleton_path.exists():
        log_info(f"SKILL_FEEDBACK 骨架已前置存在: {skeleton_path.name}")
        _refresh_events_section(skeleton_path, ver_dir)
        content = skeleton_path.read_text(encoding="utf-8")
        placeholder_count = _count_placeholders(content)
        if placeholder_count > 0:
            _emit_feedback_handoff(software, version, ver_dir, project_dir,
                "feedback_placeholders_remain",
                [f"骨架报告已生成，但有 {placeholder_count} 处 (请填写) 待补充：",
                 f"文件: {skeleton_path}",
                 "",
                 "需要填写的内容：",
                 "  - 建议 > SKILL 设计改进",
                 "  - 建议 > 模板改进",
                 "  - 建议 > 自动化补全",
                 "  - 建议 > 知识图谱覆盖",
                 "  - 情况 > 效率分析 (HANDOFF次数/重试次数/瓶颈/耗时)",
                 "  - 情况 > AI 检视结果 (摘要评估/意见数量/处理方式)",
                 "  - 情况 > 未覆盖的错误模式",
                 "",
                 f"填充后验证: python3 scripts/ohc-run.py feedback {software} {version} --resume"])
            return 1
        record_event(ver_dir, "feedback_complete_no_placeholder")
        _save_feedback_state(ver_dir, {**state, "status": "complete",
                                       "completed_at": datetime.now().isoformat(timespec="seconds")})
        print(f"\n  📋 SKILL_FEEDBACK 报告:")
        print(f"     文件: {skeleton_path}")
        print(f"     ID: {skeleton_id}")
        print(f"     状态: ✅ 完整 (0 处待填写)")
        return 0

    log_info(f"生成 SKILL_FEEDBACK 报告: {software} {version}")

    # ── Collect data ──
    bg = _collect_background(ver_dir, software, version)
    sit = _collect_situation(ver_dir, project_dir)

    # ── Git author info ──
    author_name, author_email = _get_git_author(project_dir)
    git_commit = _get_git_commit(project_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Generate feedback ID ──
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_id = _generate_feedback_id(feedback_dir)
    feedback_path = feedback_dir / f"SKILL_FEEDBACK_{feedback_id}.md"

    # ── Render and write ──
    body = _render_feedback_body(
        bg, sit, author_name, author_email,
        agent_id, timestamp, git_commit, feedback_id,
        events=state.get("events") or [])
    feedback_path.write_text(body, encoding="utf-8")
    log_ok(f"  ✅ 反馈报告已生成: {feedback_path}")

    # ── Save state ──
    _save_feedback_state(ver_dir, {**state,
        "feedback_id": feedback_id,
        "feedback_path": str(feedback_path),
        "software": software,
        "version": version,
        "status": "draft",
        "created_at": timestamp})

    # ── Check completeness ──
    placeholder_count = _count_placeholders(body)
    if placeholder_count > 0:
        log_warn(f"  ⚠️ 报告中有 {placeholder_count} 处 (请填写) 待 AI 补充")
        _emit_feedback_handoff(software, version, ver_dir, project_dir,
            "feedback_placeholders_remain",
            [f"SKILL_FEEDBACK 报告已生成，但有 {placeholder_count} 处 (请填写) 待补充：",
             f"文件: {feedback_path}",
             "",
             "需要填写的内容：",
             "  - 建议 > SKILL 设计改进",
             "  - 建议 > 模板改进",
             "  - 建议 > 自动化补全",
             "  - 建议 > 知识图谱覆盖",
             "  - 情况 > 效率分析 (HANDOFF次数/重试次数/瓶颈/耗时)",
             "  - 情况 > AI 检视结果 (摘要评估/意见数量/处理方式)",
             "  - 情况 > 未覆盖的错误模式",
             "  - 情况 > 执行概要 > conan-verify 结果",
             "",
             f"填充后验证: python3 scripts/ohc-run.py feedback {software} {version} --resume"])
        return 1

    # ── No placeholders — complete ──
    record_event(ver_dir, "feedback_complete_no_placeholder")
    _save_feedback_state(ver_dir, {**state, "status": "complete",
                                   "completed_at": timestamp})
    print(f"\n  📋 SKILL_FEEDBACK 报告:")
    print(f"     文件: {feedback_path}")
    print(f"     ID: {feedback_id}")
    print(f"     状态: ✅ 完整 (0 处待填写)")
    return 0


def feedback_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc feedback <software> <version> [--resume]"""
    parser = argparse.ArgumentParser(
        prog="ohc feedback",
        description="生成 SKILL 执行流程反馈报告 (SKILL_FEEDBACK)，含 HANDOFF 强制",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--project-dir", "-p", default=None)
    parser.add_argument("--resume", action="store_true",
                         help="从上次 HANDOFF 处恢复（检查报告完整性）")
    args = parser.parse_args(argv)
    return cmd_feedback(
        args.software,
        args.version,
        pdir=getattr(args, "project_dir", None),
        resume=getattr(args, "resume", False),
    )
