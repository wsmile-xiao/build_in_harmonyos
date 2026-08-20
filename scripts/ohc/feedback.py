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

def _load_feedback_state(ver_dir: Path) -> dict:
    """Load feedback state from .feedback-state.json."""
    state_path = ver_dir / ".feedback-state.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_feedback_state(ver_dir: Path, state: dict) -> None:
    """Save feedback state to .feedback-state.json."""
    state_path = ver_dir / ".feedback-state.json"
    state["last_updated"] = datetime.now().isoformat()
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8")


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
                          feedback_id: str) -> str:
    """Render the feedback report body from collected data."""
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
        print(f"\n  📋 SKILL_FEEDBACK 完成:")
        print(f"     文件: {feedback_path}")
        print(f"     ID: {feedback_id}")
        print(f"     状态: ✅ 完整 (0 处待填写)")
        return 0

    # ── First run: generate report ──
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
        agent_id, timestamp, git_commit, feedback_id)
    feedback_path.write_text(body, encoding="utf-8")
    log_ok(f"  ✅ 反馈报告已生成: {feedback_path}")

    # ── Save state ──
    _save_feedback_state(ver_dir, {
        "feedback_id": feedback_id,
        "feedback_path": str(feedback_path),
        "software": software,
        "version": version,
    })

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
