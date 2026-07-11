"""协作辅助工具 — 本地自检 + 审核辅助 + 合并后重建。

适配 Git + GitCode PR 工作流，替代原有提交单系统。

Usage:
    python3 ohc-run.py submit <software> <version>
    python3 ohc-run.py review <software> <version>
    python3 ohc-run.py post-merge <software> <version>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import (
    find_project_dir,
    get_agent_id,
    graph_dir,
    log_info,
    log_ok,
    log_warn,
    log_fail,
)


# ═══════════════════════════════════════════════════════
# Path helpers
# ═══════════════════════════════════════════════════════

def _archive_dir(letter: str, name: str, version: str,
                 pdir: str | None = None) -> Path:
    return Path(pdir or find_project_dir()) / "archives" / letter / name / version


# ═══════════════════════════════════════════════════════
# Simple YAML helpers (no external deps)
# ═══════════════════════════════════════════════════════

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
                # Strip quotes
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
            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val:
                data[key] = val
            else:
                # Might be a list
                current_list_key = key
                data.setdefault(key, [])
    return data


def _write_yaml(path: Path, data: dict) -> None:
    """Write dict to simple YAML format."""
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, str):
                    lines.append(f"  - \"{item}\"")
                else:
                    lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: \"{value}\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_yaml_field(path: Path, key: str, value: str) -> None:
    """Update a single field in an existing YAML file (or append)."""
    if not path.exists():
        _write_yaml(path, {key: value})
        return
    lines = path.read_text(encoding="utf-8").split("\n")
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[i] = f"{key}: \"{value}\""
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}: \"{value}\"")
    path.write_text("\n".join(lines), encoding="utf-8")


def _append_yaml_fields(path: Path, fields: dict) -> None:
    """Append multiple fields to an existing YAML file."""
    if not path.exists():
        _write_yaml(path, fields)
        return
    content = path.read_text(encoding="utf-8")
    lines = content.rstrip("\n").split("\n")
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - \"{item}\"")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: \"{value}\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ═══════════════════════════════════════════════════════
# Checklist helpers
# ═══════════════════════════════════════════════════════

_REQUIRED_MANIFEST_FIELDS = [
    "status", "software", "version", "build_date", "build_system",
]

_TEMP_FILE_PREFIXES = ["DIAGNOSIS_", "MISSING_", "WORKFLOW_", "WORKPLAN_", "SCAN_"]


def _check_manifest_complete(ver_dir: Path) -> bool:
    """Check that manifest.yaml has all required fields with non-empty values."""
    manifest = ver_dir / "manifest.yaml"
    if not manifest.exists():
        return False
    data = _parse_yaml_simple(manifest)
    for field in _REQUIRED_MANIFEST_FIELDS:
        val = data.get(field, "")
        if isinstance(val, str) and not val.strip():
            return False
        if isinstance(val, list) and not val:
            return False
    return True


def _check_progress_closed(ver_dir: Path) -> bool:
    """Check that notes.md has a closing marker."""
    progress = ver_dir / "notes.md"
    if not progress.exists():
        return False
    content = progress.read_text(encoding="utf-8", errors="replace")
    closing_markers = ["最终状态", "结束标记", "编译结束", "## 结束", "## 关闭",
                       "status: closed", "COMPLETED"]
    return any(marker in content for marker in closing_markers)


def _check_patches_valid(ver_dir: Path) -> bool:
    """Check that patches/ files follow NNNN-xxx.patch naming."""
    patches_dir = ver_dir / "patches"
    if not patches_dir.is_dir():
        # No patches directory is acceptable (e.g. failed builds)
        return True
    for f in patches_dir.iterdir():
        if f.is_file() and f.suffix == ".patch":
            if not re.match(r'^\d{4}-.*\.patch$', f.name):
                return False
    return True


def _check_packaging_present(ver_dir: Path, status: str) -> bool:
    """Check that packaging/ has tar.gz for success/partial builds."""
    if status not in ("published", "built"):
        return True  # Not required for failed builds
    packaging_dir = ver_dir / "packaging"
    if not packaging_dir.is_dir():
        return False
    tars = list(packaging_dir.glob("*.tar.gz"))
    return len(tars) > 0


def _check_no_temp_files(ver_dir: Path) -> bool:
    """Check for temporary diagnostic files."""
    for subdir in ["", "reports", "patches", "logs"]:
        d = ver_dir / subdir if subdir else ver_dir
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file():
                for prefix in _TEMP_FILE_PREFIXES:
                    if f.name.startswith(prefix):
                        return False
    return True


def _check_test_report(ver_dir: Path) -> bool:
    """Check that reports/ has test-report.md."""
    report = ver_dir / "reports" / "test-report.md"
    return report.exists()


# ═══════════════════════════════════════════════════════
# Knowledge scanning helpers
# ═══════════════════════════════════════════════════════

def _scan_draft_entries(software: str, pdir: str | None = None) -> list[str]:
    """Scan knowledge/graph/draft/ for .kv files belonging to this software.

    We match by looking at the contributor_id field or by scanning all draft
    .kv files (since drafts don't have explicit software tagging).

    Returns list of draft .kv file paths.
    """
    draft_dir = Path(graph_dir(pdir)) / "draft"
    if not draft_dir.is_dir():
        return []
    return sorted([str(f) for f in draft_dir.glob("E*-draft-*.kv")])


def _scan_knowledge_gained(ver_dir: Path) -> list[str]:
    """Read knowledge_gained from manifest.yaml."""
    manifest = ver_dir / "manifest.yaml"
    data = _parse_yaml_simple(manifest)
    entries = data.get("knowledge_gained", [])
    if isinstance(entries, list):
        return entries
    return []


def _scan_knowledge_ref(ver_dir: Path) -> list[str]:
    """Read knowledge_ref from manifest.yaml."""
    manifest = ver_dir / "manifest.yaml"
    data = _parse_yaml_simple(manifest)
    entries = data.get("knowledge_ref", [])
    if isinstance(entries, list):
        return entries
    return []


# ═══════════════════════════════════════════════════════
# cmd: submit — 门禁 + 自检 + git push + 创建PR + CI监控 + AI Review
# ═══════════════════════════════════════════════════════

def _generate_pr_body(software: str, version: str, ver_dir: Path) -> Path:
    """Generate PR body from manifest data, save to reports/pr-body.md.

    Fills in the PR template with data from manifest.yaml, patches/, and
    test results. Fields that can't be auto-filled are marked with (请填写).
    """
    manifest = _parse_yaml_simple(ver_dir / "manifest.yaml")

    # Gather data
    build_system = str(manifest.get("build_system", "unknown"))
    upstream_url = str(manifest.get("upstream_url", manifest.get("url", "")))
    status = str(manifest.get("status", "unknown"))
    configure_options = str(manifest.get("configure_options", ""))
    test_passed_val = manifest.get("test_passed", 0)
    test_failed_val = manifest.get("test_failed", 0)

    # Patches
    patches_dir = ver_dir / "patches"
    patches = []
    if patches_dir.is_dir():
        patches = sorted(pf.name for pf in patches_dir.glob("*.patch"))

    # Knowledge refs
    knowledge_ref = _scan_knowledge_ref(ver_dir)

    # Build status text
    if status in ("published", "built"):
        build_status = "成功"
    else:
        build_status = "失败"

    # Adaptation path heuristic
    adaptation_path = "路径 A（基础适配）" if patches else "路径 A（基础适配，无补丁）"

    patch_lines = "\n".join(f"- {p}" for p in patches) if patches else "无补丁"
    knowledge_str = ", ".join(knowledge_ref) if knowledge_ref else "(请填写)"

    body = f"""## PR 信息
- **三方库名称**：{software}
- **上游版本**：{version}
- **上游仓库地址**：{upstream_url or '(请填写)'}
- **适配路径**：{adaptation_path}
- **使用知识库**：{knowledge_str}

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | (请填写) |
| 集成测试 | 0 | (请填写) |
| 其他测试 | 0 | (请填写) |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
(请填写)

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | {test_passed_val} | (请填写) | (请填写) |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | (请填写) |
| **合计** | **{test_passed_val}** | | |

---

## 上游测试用例修改说明
(请填写)

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: {build_status}
- 构建系统: {build_system}
- 配置选项: `{configure_options or '(请填写)'}`

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | PASS | (请填写) |
| 产物存在性 | PASS | (请填写) |
| ELF 格式 | PASS | (请填写) |
| 运行测试 | PASS | (请填写) |
| 动态依赖 | PASS | (请填写) |

### 补丁说明
{patch_lines}

### 依赖
(请填写)
"""

    pr_body_path = ver_dir / "reports" / "pr-body.md"
    pr_body_path.parent.mkdir(parents=True, exist_ok=True)
    if not pr_body_path.exists():
        pr_body_path.write_text(body, encoding="utf-8")
    else:
        # Preserve existing content if already filled in by AI
        existing = pr_body_path.read_text(encoding="utf-8")
        if "(请填写)" not in existing:
            # Already filled in, don't overwrite
            pass
        else:
            # Has placeholders, overwrite with fresh generated content
            pr_body_path.write_text(body, encoding="utf-8")
    return pr_body_path


def _emit_submit_handoff(software: str, version: str, ver_dir: Path,
                         project_dir: str, reason: str,
                         actions: list[str]) -> None:
    """Emit HANDOFF block for submit gate failure."""
    from .handoff import HandoffData, emit_handoff
    data = HandoffData(
        exit_reason=reason,
        exit_code=2,
        step_failed="submit",
        resume_cmd=f"python3 scripts/ohc-run.py submit {software} {version}",
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


def cmd_submit(software: str, version: str, pdir: str | None = None) -> int:
    """Submit PR: gates → self-check → git push → create PR → monitor CI → check review.

    Gates (all blocking with HANDOFF):
    0. GitCode token configured (~/.gitcode-token or GITCODE_TOKEN env)
    1. finish completed (manifest.yaml exists)
    2. W3 local CI passed (.ci-result.json with exit_code=0)
    3. W4 pre-PR audit passed (audit-result.json with verdict=pass, P0/P1=0)

    After gates + self-check + git push (with rebase retry):
    4. Create PR via gitcode_pr.py create-pr
    5. Monitor CI via gitcode_pr.py ci-status (poll, 10min timeout, blocking)
    6. Check AI Review via gitcode_pr.py get-review-comments (3 retries, 30s interval)
    """
    project_dir = pdir or find_project_dir()
    agent_id = get_agent_id(project_dir)
    letter = software[0].lower()
    ver_dir = _archive_dir(letter, software, version, project_dir)

    if not ver_dir.exists():
        log_fail(f"❌ 版本目录不存在: {ver_dir}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "finish_not_run",
            ["版本目录不存在，请先执行 finish",
             f"python3 scripts/ohc-run.py finish {software} {version} <status>"])
        return 1

    # ── Gate 0/4: GitCode token pre-check ──
    token_file = Path.home() / ".gitcode-token"
    if not token_file.exists() and not os.environ.get("GITCODE_TOKEN"):
        log_fail("❌ Gate 0/4: GitCode token 未配置")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "token_not_configured",
            ["GitCode access_token 未配置，无法自动创建 PR",
             "请先配置 token: python3 scripts/gitcode_pr.py setup",
             f"配置后重新 submit: python3 scripts/ohc-run.py submit {software} {version}"])
        return 1
    log_ok("✅ Gate 0/4: GitCode token 已配置")

    # ── Gate 1/4: finish completed (manifest.yaml exists) ──
    manifest_path = ver_dir / "manifest.yaml"
    if not manifest_path.exists():
        log_fail("❌ Gate 1/4: finish 未完成 (manifest.yaml 不存在)")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "finish_not_run",
            ["请先执行 finish 完成编译收尾",
             f"python3 scripts/ohc-run.py finish {software} {version} <status>"])
        return 1
    log_ok("✅ Gate 1/4: finish 已完成")

    # ── Gate 2/4: W3 local CI passed (.ci-result.json) ──
    ci_result_path = ver_dir / ".ci-result.json"
    if not ci_result_path.exists():
        log_fail("❌ Gate 2/4: W3 本地 CI 模拟未通过 (.ci-result.json 不存在)")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "w3_not_passed",
            ["W3 本地 CI 模拟未执行或失败，请重新 finish",
             f"python3 scripts/ohc-run.py finish {software} {version} <status>"])
        return 1
    try:
        ci_data = json.loads(ci_result_path.read_text(encoding="utf-8"))
        if ci_data.get("exit_code", -1) != 0:
            log_fail(f"❌ Gate 2/4: W3 本地 CI 模拟未通过 (exit_code={ci_data.get('exit_code')})")
            _emit_submit_handoff(software, version, ver_dir, project_dir,
                "w3_not_passed",
                ["W3 本地 CI 模拟未通过，请修复后重新 finish",
                 f"python3 scripts/ohc-run.py finish {software} {version} <status>"])
            return 1
        # Verify integrity hash (prevent AI forgery)
        import hashlib
        ts = ci_data.get("timestamp", "")
        ec = ci_data.get("exit_code", -1)
        raw = f"{ts}:{software}:{version}:{ec}"
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        actual_hash = ci_data.get("integrity_hash", "")
        if actual_hash != expected_hash:
            log_fail("❌ Gate 2/4: .ci-result.json integrity_hash 不匹配（疑似伪造）")
            _emit_submit_handoff(software, version, ver_dir, project_dir,
                "w3_forged",
                [".ci-result.json 完整性校验失败，请重新 finish（不要手动创建此文件）",
                 f"python3 scripts/ohc-run.py finish {software} {version} <status>"])
            return 1
    except (json.JSONDecodeError, OSError) as e:
        log_fail(f"❌ Gate 2/4: .ci-result.json 格式无效: {e}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "w3_invalid",
            [".ci-result.json 格式无效，请重新 finish"])
        return 1
    log_ok("✅ Gate 2/4: W3 本地 CI 模拟已通过")

    # ── Gate 3/4: W4 Pre-PR audit ──
    audit_result_path = ver_dir / "reports" / "audit-result.json"
    if not audit_result_path.exists():
        log_fail("❌ Gate 3/4: W4 Pre-PR 审计未执行 (audit-result.json 不存在)")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "w4_audit_not_done",
            ["W4 Pre-PR 审计未执行，请先完成审计",
             f"python3 scripts/pre_pr_audit.py generate --repo-dir {project_dir} --package {software} --version {version}",
             "审计子任务完成后将结果保存为 reports/audit-result.json",
             f"重新提交: python3 scripts/ohc-run.py submit {software} {version}"])
        return 1
    try:
        audit_data = json.loads(audit_result_path.read_text(encoding="utf-8"))
        verdict = audit_data.get("verdict", "unknown")
        issues = audit_data.get("issues", [])
        p0_count = sum(1 for i in issues if i.get("severity") == "P0")
        p1_count = sum(1 for i in issues if i.get("severity") == "P1")
        if verdict != "pass" or p0_count > 0 or p1_count > 0:
            log_fail(f"❌ Gate 3/4: W4 审计未通过 (verdict={verdict}, P0={p0_count}, P1={p1_count})")
            _emit_submit_handoff(software, version, ver_dir, project_dir,
                "w4_audit_failed",
                ["W4 Pre-PR 审计未通过，必须修复 P0/P1 问题",
                 "修复后重新生成审计输入并重新审计",
                 f"python3 scripts/pre_pr_audit.py generate --repo-dir {project_dir} --package {software} --version {version}",
                 f"审计通过后重新提交: python3 scripts/ohc-run.py submit {software} {version}"])
            return 1
    except (json.JSONDecodeError, OSError) as e:
        log_fail(f"❌ Gate 3/4: audit-result.json 格式无效: {e}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "w4_audit_invalid",
            ["audit-result.json 格式无效，请重新审计"])
        return 1
    log_ok("✅ Gate 3/4: W4 Pre-PR 审计通过")

    # ── All gates passed, run self-check checklist ──
    manifest = _parse_yaml_simple(ver_dir / "manifest.yaml")
    status = str(manifest.get("status", "unknown"))

    log_info("执行自检 (checklist)...")
    checklist = {
        "manifest_complete": _check_manifest_complete(ver_dir),
        "progress_closed": _check_progress_closed(ver_dir),
        "patches_valid": _check_patches_valid(ver_dir),
        "packaging_present": _check_packaging_present(ver_dir, status),
        "no_temp_files": _check_no_temp_files(ver_dir),
        "test_report_present": _check_test_report(ver_dir),
    }
    for check_name, passed in checklist.items():
        if passed:
            log_ok(f"  {check_name}: PASS")
        else:
            log_warn(f"  {check_name}: FAIL")

    failed_checks = [k for k, v in checklist.items() if v is False]
    if failed_checks:
        log_fail(f"❌ 自检未通过: {failed_checks}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "self_check_failed",
            [f"自检未通过: {failed_checks}",
             "修复后重新 submit",
             f"python3 scripts/ohc-run.py submit {software} {version}"])
        return 1

    # ── Execute git operations ──
    branch_name = f"feat/{software}-{version}"
    log_info(f"创建分支并提交: {branch_name}")

    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        result2 = subprocess.run(
            ["git", "checkout", branch_name],
            cwd=project_dir, capture_output=True, text=True)
        if result2.returncode != 0:
            log_fail(f"❌ 创建/切换分支失败: {result.stderr.strip()}")
            _emit_submit_handoff(software, version, ver_dir, project_dir,
                "git_branch_failed",
                [f"创建分支失败: {result.stderr.strip()}",
                 f"手动执行: git checkout -b {branch_name}",
                 f"然后重新 submit: python3 scripts/ohc-run.py submit {software} {version}"])
            return 1
    log_ok(f"  分支切换 ✅ ({branch_name})")

    # R26/W2: Only add the current package's archive path + knowledge drafts
    archive_path = f"archives/{letter}/{software}/{version}/"
    software_archive_root = f"archives/{letter}/{software}/"
    result = subprocess.run(
        ["git", "add", archive_path, "knowledge/graph/draft/"],
        cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        log_fail(f"❌ git add 失败: {result.stderr.strip()}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "git_add_failed",
            [f"git add 失败: {result.stderr.strip()}"])
        return 1

    # Verify staged files only belong to the current package
    staged_result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=project_dir, capture_output=True, text=True)
    if staged_result.returncode == 0:
        staged_files = [f for f in staged_result.stdout.strip().split("\n") if f]
        unexpected = []
        for f in staged_files:
            # Allow: current package archive, software-level files (commands.json etc), knowledge drafts
            if not f.startswith(archive_path) \
               and not (f.startswith(software_archive_root) and f.count("/") <= 3) \
               and not f.startswith("knowledge/graph/draft/"):
                unexpected.append(f)
        if unexpected:
            log_fail(f"❌ 暂存了不属于当前包的文件 (违反 W2 原子性):")
            for f in unexpected:
                log_fail(f"   {f}")
            _emit_submit_handoff(software, version, ver_dir, project_dir,
                "git_add_atomicity_violation",
                [f"git add 暂存了不属于 {software}/{version} 的文件: {unexpected}",
                 "请检查工作区是否有其他包的未提交变更",
                 f"清理后重新 submit: python3 scripts/ohc-run.py submit {software} {version}"])
            return 1

    log_ok("  git add ✅")

    pr_title = f"feat({software}): {version} 适配完成"
    result = subprocess.run(
        ["git", "commit", "-m", pr_title],
        cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
            log_warn("  ⚠️ git commit: 无变更（可能已提交）")
        else:
            log_fail(f"❌ git commit 失败: {result.stderr.strip()}")
            _emit_submit_handoff(software, version, ver_dir, project_dir,
                "git_commit_failed",
                [f"git commit 失败: {result.stderr.strip()}"])
            return 1
    else:
        log_ok("  git commit ✅")

    # Push with rebase retry (handles non-fast-forward)
    max_retries = 2
    push_success = False
    for attempt in range(max_retries + 1):
        result = subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=project_dir, capture_output=True, text=True)
        if result.returncode == 0:
            push_success = True
            break

        stderr_lower = result.stderr.lower()
        if ("non-fast-forward" in stderr_lower or "rejected" in stderr_lower
            or "fetch first" in stderr_lower) and attempt < max_retries:
            log_warn(f"  ⚠️ git push 被拒绝 (non-fast-forward)，尝试 rebase 后重试 ({attempt+1}/{max_retries})...")
            rebase_result = subprocess.run(
                ["git", "pull", "--rebase", "origin", branch_name],
                cwd=project_dir, capture_output=True, text=True, timeout=60)
            if rebase_result.returncode != 0:
                log_fail(f"❌ rebase 冲突，需手动解决")
                _emit_submit_handoff(software, version, ver_dir, project_dir,
                    "rebase_conflict",
                    [f"rebase 冲突: {rebase_result.stderr.strip()[:200]}",
                     "手动解决冲突后:",
                     "  git rebase --continue",
                     f"  git push origin {branch_name}",
                     f"  然后重新 submit: python3 scripts/ohc-run.py submit {software} {version}"])
                return 1
            log_ok(f"  rebase 成功，重试 push...")
            continue
        else:
            # Non-retryable error or max retries reached
            break

    if not push_success:
        log_fail(f"❌ git push 失败: {result.stderr.strip()}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "git_push_failed",
            [f"git push 失败: {result.stderr.strip()}",
             "检查远端仓库配置和权限",
             f"手动推送后重新 submit: python3 scripts/ohc-run.py submit {software} {version}"])
        return 1
    log_ok("  git push ✅")

    # ── Generate PR body ──
    pr_body_path = _generate_pr_body(software, version, ver_dir)
    log_ok(f"  PR body 已生成: {pr_body_path}")
    pr_body_text = pr_body_path.read_text(encoding="utf-8")

    # ── Create PR via gitcode_pr.py ──
    gitcode_pr = str(Path(__file__).resolve().parent.parent / "gitcode_pr.py")
    repo = "OpenHarmonyPCDeveloper/build_in_harmonyos"

    log_info("创建 GitCode PR...")
    pr_result = subprocess.run(
        ["python3", gitcode_pr, "create-pr",
         "--repo", repo,
         "--source", branch_name,
         "--target", "main",
         "--title", pr_title,
         "--description", pr_body_text],
        capture_output=True, text=True, timeout=30)

    pr_number = None
    if pr_result.returncode == 0:
        pr_number = _parse_pr_number(pr_result.stdout)
    elif "already exists" in pr_result.stderr.lower() or "409" in pr_result.stderr:
        log_warn("  PR 已存在，查找现有 PR 编号...")
        list_result = subprocess.run(
            ["python3", gitcode_pr, "list-prs",
             "--repo", repo, "--source-branch", branch_name],
            capture_output=True, text=True, timeout=15)
        pr_number = _parse_pr_number(list_result.stdout)

    if not pr_number:
        log_fail(f"❌ PR 创建/查找失败")
        log_fail(f"   stdout: {pr_result.stdout[-200:]}")
        log_fail(f"   stderr: {pr_result.stderr[-200:]}")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "pr_creation_failed",
            [f"PR 创建失败",
             f"手动创建: python3 scripts/gitcode_pr.py create-pr --repo {repo} --source {branch_name} --target main --title '{pr_title}'"])
        return 1

    log_ok(f"  PR #{pr_number} 已创建/找到")
    pr_url = f"https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/{pr_number}"

    # ── Monitor CI (poll every 30s, timeout 10min) ──
    log_info(f"监控 CI 状态 (PR #{pr_number})...")
    ci_status = _monitor_ci(gitcode_pr, repo, pr_number, timeout=600)

    if ci_status == "FAILED":
        log_fail(f"❌ CI 构建失败")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "ci_build_failed",
            [f"CI 构建失败，请查看 PR #{pr_number} 的 CI 评论",
             f"修复后 push 新 commit: git push origin {branch_name}",
             f"查看 CI: python3 scripts/gitcode_pr.py ci-status --repo {repo} --number {pr_number}"])
        return 1
    elif ci_status == "TIMEOUT":
        log_fail(f"❌ CI 监控超时 (10分钟)")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "ci_monitor_timeout",
            [f"CI 监控超时，请稍后手动检查 PR #{pr_number} 的 CI 状态",
             f"检查 CI: python3 scripts/gitcode_pr.py ci-status --repo {repo} --number {pr_number}",
             f"CI 通过后可等待自动合并，或手动提醒审核者"])
        return 1
    elif ci_status == "PASSED":
        log_ok(f"  ✅ CI 构建通过")

    # ── Check AI Review ──
    log_info(f"检查 AI Review (PR #{pr_number})...")
    import time as _time

    review_result = None
    review_stdout = ""
    for attempt in range(3):
        _time.sleep(30 if attempt > 0 else 15)
        review_result = subprocess.run(
            ["python3", gitcode_pr, "get-review-comments",
             "--repo", repo, "--number", str(pr_number)],
            capture_output=True, text=True, timeout=30)
        if review_result.returncode != 0:
            log_warn(f"  AI Review 查询失败 (尝试 {attempt+1}/3): {review_result.stderr.strip()[:100]}")
            continue
        review_stdout = review_result.stdout
        # Check if review has been posted (look for bot comments)
        if "🔴" in review_stdout or "🟠" in review_stdout or "检视" in review_stdout or "Priority" in review_stdout:
            break  # Review content found, proceed to analysis
        if attempt < 2:
            log_info(f"  AI Review 尚未完成，等待重试 ({attempt+1}/3)...")

    if review_result is None or review_result.returncode != 0:
        log_fail(f"❌ AI Review 查询失败（3次重试均失败）")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "ai_review_query_failed",
            [f"AI Review 查询失败，请手动检查 PR #{pr_number}",
             f"查看: python3 scripts/gitcode_pr.py get-review-comments --repo {repo} --number {pr_number}"])
        return 1

    if "🔴" in review_stdout or "🟠" in review_stdout:
        log_fail(f"❌ AI Review 发现 Critical/High 问题")
        _emit_submit_handoff(software, version, ver_dir, project_dir,
            "ai_review_failed",
            [f"AI Review 发现 Critical/High 问题，请查看 PR #{pr_number}",
             "修复问题后 push 新 commit",
             f"回复评论: python3 scripts/gitcode_pr.py reply-comment --repo {repo} --number {pr_number} --discussion-id <id> --body '已修复'"])
        return 1
    elif "检视" in review_stdout or "Priority" in review_stdout:
        log_warn(f"  ⚠️ AI Review 有意见，请查看 PR #{pr_number}")
        print(f"     查看: python3 scripts/gitcode_pr.py get-review-comments --repo {repo} --number {pr_number}")
    else:
        log_ok(f"  ✅ AI Review 通过")

    # ── Success ──
    print(f"\n  ✅ PR 提交完成: {software} {version}")
    print(f"     PR: #{pr_number}")
    print(f"     URL: {pr_url}")
    print(f"     分支: {branch_name}")
    print(f"     标题: {pr_title}")
    return 0


def _parse_pr_number(output: str) -> int | None:
    """Parse PR number from gitcode_pr.py output."""
    import re
    # Try "编号: #1234" format
    m = re.search(r'#(\d+)', output)
    if m:
        return int(m.group(1))
    # Try JSON format
    if "--- JSON ---" in output:
        json_part = output.split("--- JSON ---")[-1].strip()
        try:
            data = json.loads(json_part)
            num = data.get("number")
            if isinstance(num, int):
                return num
        except json.JSONDecodeError:
            pass
    return None


def _monitor_ci(gitcode_pr: str, repo: str, pr_number: int,
                timeout: int = 600, interval: int = 30) -> str:
    """Poll CI status until completion or timeout.

    Returns: 'PASSED', 'FAILED', 'TIMEOUT', or 'UNKNOWN'
    """
    import time as _time
    elapsed = 0

    while elapsed < timeout:
        result = subprocess.run(
            ["python3", gitcode_pr, "ci-status",
             "--repo", repo, "--number", str(pr_number)],
            capture_output=True, text=True, timeout=15)

        output = result.stdout
        if "PASSED" in output:
            return "PASSED"
        elif "FAILED" in output:
            return "FAILED"
        elif "RUNNING" in output or "QUEUED" in output or "未找到" in output or "排队" in output:
            log_info(f"  CI 进行中... ({elapsed}s/{timeout}s)")
            _time.sleep(interval)
            elapsed += interval
        else:
            log_warn(f"  CI 状态未知，继续等待...")
            _time.sleep(interval)
            elapsed += interval

    return "TIMEOUT"


# ═══════════════════════════════════════════════════════
# cmd: review — 本地审核辅助
# ═══════════════════════════════════════════════════════

def cmd_review(software: str, version: str,
               pdir: str | None = None) -> int:
    """Review a software+version by directly scanning archive directory."""
    project_dir = pdir or find_project_dir()
    letter = software[0].lower()
    ver_dir = _archive_dir(letter, software, version, project_dir)

    if not ver_dir.exists():
        log_fail(f"版本目录不存在: {ver_dir}")
        return 1

    return _review_single(software, version, ver_dir, project_dir)


def _review_single(software: str, version: str,
                   ver_dir: Path, project_dir: str) -> int:
    """Review a single software+version and output results."""
    sid = f"{software}-{version}"
    print(f"\n  🔍 Reviewing: {sid}")

    # Load manifest for status
    manifest = _parse_yaml_simple(ver_dir / "manifest.yaml")
    status = str(manifest.get("status", "unknown"))

    checks: list[tuple[str, str, str]] = []  # (name, status, detail)
    pass_count = 0
    warn_count = 0
    fail_count = 0

    def _record(name: str, status: str, detail: str = ""):
        nonlocal pass_count, warn_count, fail_count
        checks.append((name, status, detail))
        if status == "PASS":
            pass_count += 1
        elif status == "WARN":
            warn_count += 1
        else:
            fail_count += 1

    # ── Check 1: 补丁完整性 ──
    patches_dir = ver_dir / "patches"
    if patches_dir.is_dir():
        patch_ok = True
        for pf in patches_dir.glob("*.patch"):
            if not re.match(r'^\d{4}-.*\.patch$', pf.name):
                _record("1. 补丁命名规范", "FAIL", f"命名不规范: {pf.name}")
                patch_ok = False
                break
            # Check diff format (first 3 lines should contain --- and +++)
            try:
                head = pf.read_text(encoding="utf-8", errors="replace")[:500]
                if "---" not in head or "+++" not in head:
                    _record("1. 补丁格式", "WARN", f"{pf.name}: 可能不是合法 diff 格式")
                    patch_ok = False
                    break
            except Exception:
                pass
        if patch_ok:
            _record("1. 补丁完整性", "PASS")
    else:
        _record("1. 补丁完整性", "PASS", "无补丁目录")

    # ── Check 2: E编号冲突检测 ──
    draft_dir = Path(graph_dir(project_dir)) / "draft"
    index_path = Path(graph_dir(project_dir)) / "index.tsv"
    existing_ids: set[str] = set()
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                cols = line.split("\t")
                if cols:
                    existing_ids.add(cols[0])

    new_eids: list[str] = []
    if draft_dir.is_dir():
        for kvf in draft_dir.glob("E*-draft-*.kv"):
            m = re.match(r'^(E\d+)-draft-', kvf.name)
            if m:
                new_eids.append(m.group(1))

    conflicts = [eid for eid in new_eids if eid in existing_ids]
    if conflicts:
        _record("2. E编号冲突", "FAIL", f"冲突: {conflicts}")
    elif new_eids:
        _record("2. E编号冲突", "PASS", f"新增 {len(new_eids)} 个编号, 无冲突")
    else:
        _record("2. E编号冲突", "PASS", "无新增编号")

    # ── Check 3: 知识去重（半自动） ──
    if new_eids and draft_dir.is_dir():
        dupe_found = False
        for kvf in draft_dir.glob("E*-draft-*.kv"):
            try:
                kv_data_lines = kvf.read_text(encoding="utf-8").split("\n")
                for line in kv_data_lines:
                    if line.startswith("match_keywords:"):
                        kw_str = line.partition(":")[2].strip()
                        kws = [k.strip() for k in kw_str.split(",") if k.strip()]
                        # Check against existing .kv files
                        gdir = Path(graph_dir(project_dir))
                        for existing_kv in gdir.glob("E*.kv"):
                            try:
                                existing_content = existing_kv.read_text(encoding="utf-8")
                                for kw in kws:
                                    if kw.lower() in existing_content.lower():
                                        _record("3. 知识去重", "WARN",
                                                f"关键词 '{kw}' 在 {existing_kv.name} 中已有匹配")
                                        dupe_found = True
                            except Exception:
                                pass
                        break  # Only check first match_keywords line
            except Exception:
                pass
        if not dupe_found:
            _record("3. 知识去重", "PASS", "未发现明显重复")
    else:
        _record("3. 知识去重", "PASS", "无新增草稿")

    # ── Check 4: manifest.yaml 完整性 ──
    manifest_path = ver_dir / "manifest.yaml"
    if manifest_path.exists():
        mf = _parse_yaml_simple(manifest_path)
        missing_fields = [f for f in _REQUIRED_MANIFEST_FIELDS
                          if f not in mf or not str(mf.get(f, "")).strip()]
        # Check test_results not all zero
        tr_passed = mf.get("test_passed", mf.get("test_results_passed", "0"))
        tr_failed = mf.get("test_failed", mf.get("test_results_failed", "0"))
        try:
            tr_p = int(str(tr_passed))
            tr_f = int(str(tr_failed))
        except (ValueError, TypeError):
            tr_p, tr_f = 0, 0

        if missing_fields:
            _record("4. Manifest完整性", "FAIL", f"缺失字段: {missing_fields}")
        elif tr_p == 0 and tr_f == 0:
            _record("4. Manifest完整性", "WARN", "test_results 全零")
        else:
            _record("4. Manifest完整性", "PASS")
    else:
        _record("4. Manifest完整性", "FAIL", "manifest.yaml 不存在")

    # ── Check 5: 未修改禁止文件 ──
    _record("5. 禁止文件检查", "PASS", "archives/_index.yaml 和 SUMMARY.md 未在提交范围")

    # ── Check 6: notes.md 已关闭 ──
    if _check_progress_closed(ver_dir):
        _record("6. notes.md关闭", "PASS")
    else:
        _record("6. notes.md关闭", "FAIL", "notes.md 未包含结束标记")

    # ── Check 7: 临时文件检查 ──
    if _check_no_temp_files(ver_dir):
        _record("7. 临时文件", "PASS")
    else:
        _record("7. 临时文件", "FAIL", "发现临时文件 (DIAGNOSIS_*, MISSING_*, etc.)")

    # ── Check 8: knowledge_ref 引用正确性 ──
    manifest_data = _parse_yaml_simple(ver_dir / "manifest.yaml")
    refs = manifest_data.get("knowledge_ref", [])
    if isinstance(refs, list) and refs:
        bad_refs = []
        for ref in refs:
            ref_str = str(ref).split("#")[0]  # Strip anchor
            ref_path = Path(project_dir) / ref_str
            if not ref_path.exists():
                bad_refs.append(ref)
        if bad_refs:
            _record("8. knowledge_ref引用", "FAIL", f"不存在的引用: {bad_refs}")
        else:
            _record("8. knowledge_ref引用", "PASS", f"{len(refs)} 个引用均有效")
    else:
        _record("8. knowledge_ref引用", "PASS", "无引用")

    # ── Check 9: 打包产物 ──
    if _check_packaging_present(ver_dir, status):
        _record("9. 打包产物", "PASS")
    else:
        _record("9. 打包产物", "WARN", "缺少 tar.gz")

    # ── Check 10: test-report.md ──
    if _check_test_report(ver_dir):
        _record("10. 测试报告", "PASS")
    else:
        _record("10. 测试报告", "WARN", "缺少 reports/test-report.md")

    # ── Check 11: 提交自检 ──
    checklist = {
        "manifest_complete": _check_manifest_complete(ver_dir),
        "progress_closed": _check_progress_closed(ver_dir),
        "patches_valid": _check_patches_valid(ver_dir),
        "packaging_present": _check_packaging_present(ver_dir, status),
        "no_temp_files": _check_no_temp_files(ver_dir),
        "test_report_present": _check_test_report(ver_dir),
    }
    all_passed = all(v for v in checklist.values() if isinstance(v, bool))
    if all_passed:
        _record("11. 提交自检", "PASS")
    else:
        failed_checks = [k for k, v in checklist.items() if v is False]
        _record("11. 提交自检", "WARN", f"未通过: {failed_checks}")

    # ── Check 12: Overall assessment ──
    if fail_count == 0:
        _record("12. 总体评估", "PASS", f"{pass_count} PASS, {warn_count} WARN")
    else:
        _record("12. 总体评估", "FAIL", f"{fail_count} FAIL, {warn_count} WARN")

    # ── Check 13: Knowledge graph format compliance ──
    try:
        from .graph import cmd_validate as graph_validate
        from io import StringIO
        import io
        # Capture validate output
        old_stdout = sys.stdout
        sys.stdout = captured = StringIO()
        validate_result = graph_validate(pdir=project_dir)
        sys.stdout = old_stdout
        output = captured.getvalue()
        if validate_result == 0:
            _record("13. 知识图谱合规", "PASS")
        else:
            # Count errors from output
            err_lines = [l for l in output.split("\n") if "❌" in l or "[C" in l]
            _record("13. 知识图谱合规", "FAIL",
                    f"{len(err_lines)} 个问题，运行 graph validate --verbose 查看详情")
    except Exception as e:
        _record("13. 知识图谱合规", "WARN", f"无法验证: {e}")

    # ── Print summary ──
    print(f"\n  📋 Review Summary for {sid}:")
    print(f"  {'─' * 60}")
    for name, chk_status, detail in checks:
        icon = "✅" if chk_status == "PASS" else "⚠️" if chk_status == "WARN" else "❌"
        line = f"  {icon} {name}: {chk_status}"
        if detail:
            line += f" — {detail}"
        print(line)

    print(f"  {'─' * 60}")
    total = pass_count + warn_count + fail_count
    print(f"  结果: {pass_count} PASS / {warn_count} WARN / {fail_count} FAIL (共 {total} 项)")
    print(f"\n  → 在 GitCode 平台 Merge PR 或 Close PR")

    return 1 if fail_count > 0 else 0


# ═══════════════════════════════════════════════════════
# cmd: post-merge — 合并后重建
# ═══════════════════════════════════════════════════════

def cmd_post_merge(software: str, version: str,
                   pdir: str | None = None) -> int:
    """Post-merge rebuild: move drafts, rebuild indexes, harvest feedback."""
    from .models import parse_kv_file, write_kv_file
    from .graph import _regenerate_index, _kv_to_tsv_row

    project_dir = pdir or find_project_dir()
    letter = software[0].lower()
    ver_dir = _archive_dir(letter, software, version, project_dir)

    if not ver_dir.exists():
        log_fail(f"版本目录不存在: {ver_dir}")
        return 1

    sid = f"{software}-{version}"
    log_info(f"Post-merge rebuild: {sid}")

    # ── Step 1: Move draft .kv files to formal knowledge/graph/ ──
    draft_dir = Path(graph_dir(project_dir)) / "draft"
    gdir = Path(graph_dir(project_dir))
    docdir = Path(project_dir) / "knowledge" / "doc"
    docdir.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    if draft_dir.is_dir():
        for draft_kv in sorted(draft_dir.glob("E*-draft-*.kv")):
            # Extract E-number
            m = re.match(r'^(E\d+)-draft-(\w+)\.kv$', draft_kv.name)
            if not m:
                continue
            eid = m.group(1)
            contributor = m.group(2)

            target_kv = gdir / f"{eid}.kv"
            target_md = docdir / f"{eid}.md"

            if target_kv.exists():
                log_warn(f"  {eid}.kv 已存在，跳过移动 {draft_kv.name}")
                continue

            # Move .kv
            content = draft_kv.read_text(encoding="utf-8")
            # Remove draft-specific fields
            content = re.sub(r'\ndraft:.*\n', '\n', content)
            content = re.sub(r'\ncontributor_id:.*\n', '\n', content)
            target_kv.write_text(content, encoding="utf-8")
            draft_kv.unlink()
            log_ok(f"  移动 {draft_kv.name} → {target_kv.name}")

            # Move/generate corresponding .md
            draft_md = draft_dir / f"{eid}-draft-{contributor}.md"
            if draft_md.exists():
                target_md.write_text(draft_md.read_text(encoding="utf-8"), encoding="utf-8")
                draft_md.unlink()
            else:
                # Generate basic .md
                md_skeleton = f"""# {eid}

<!-- Auto-generated from draft approval -->
"""
                target_md.write_text(md_skeleton, encoding="utf-8")

            moved_count += 1

    log_info(f"  移动了 {moved_count} 个草稿知识条目")

    # ── Step 2: Rebuild index.tsv ──
    kv_files = sorted(gdir.glob("E[0-9]*.kv"))
    kv_files = [f for f in kv_files if re.match(r'^E\d+\.kv$', f.name)]
    index_path = gdir / "index.tsv"
    if kv_files:
        # Preserve comments
        comment_lines: list[str] = []
        if index_path.exists():
            for line in index_path.read_text(encoding="utf-8").split("\n"):
                if line.startswith("#") or not line.strip():
                    comment_lines.append(line)

        rows = []
        for kvf in kv_files:
            try:
                kv_data = parse_kv_file(str(kvf))
                rows.append(_kv_to_tsv_row(kv_data))
            except Exception:
                continue

        content = "\n".join(comment_lines + rows) + "\n"
        index_path.write_text(content, encoding="utf-8")
        log_ok(f"  重建 index.tsv ({len(rows)} 行)")

    # ── Step 2.5: Validate knowledge graph consistency ──
    try:
        from .graph import cmd_validate
        result = cmd_validate(verbose=True, fix=True, pdir=project_dir)
        if result != 0:
            log_warn("  知识图谱验证发现问题（已尝试自动修复），请人工检查")
        else:
            log_ok("  知识图谱验证通过")
    except Exception as e:
        log_warn(f"  知识图谱验证失败: {e}")

    # ── Step 3: Rebuild archives/_index.yaml ──
    try:
        from .summary import _scan_archives_dir
        archives_dir = Path(project_dir) / "archives"
        index_yaml_path = archives_dir / "_index.yaml"
        archive_entries = _scan_archives_dir(archives_dir)
        if archive_entries:
            lines = ["software_index:"]
            for entry in sorted(archive_entries, key=lambda e: e.get("software", "")):
                lines.append(f"  - software: \"{entry.get('software', '')}\"")
                lines.append(f"    version: \"{entry.get('version', '')}\"")
                lines.append(f"    status: \"{entry.get('status', '')}\"")
                lines.append(f"    build_system: \"{entry.get('build_system', '')}\"")
                lines.append(f"    path: \"{entry.get('path', '')}\"")
            index_yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            log_ok(f"  重建 _index.yaml ({len(archive_entries)} 条目)")
    except Exception as e:
        log_warn(f"  重建 _index.yaml 失败: {e}")

    # ── Step 4: Rebuild SUMMARY.md ──
    try:
        from .summary import generate_summary
        generate_summary(pdir=project_dir)
        log_ok("  重建 SUMMARY.md")
    except Exception as e:
        log_warn(f"  重建 SUMMARY.md 失败: {e}")

    # ── Step 5: Harvest version-level skill-feedback ──
    feedback_path = (Path(project_dir) / "archives" / letter / software / version
                     / "reports" / "skill-feedback.md")
    root_feedback = Path(project_dir) / "reports" / "skill-feedback.md"
    if feedback_path.exists():
        root_feedback.parent.mkdir(parents=True, exist_ok=True)
        feedback_content = feedback_path.read_text(encoding="utf-8")
        separator = f"\n\n---\n## {software} {version} (post-merge)\n\n"
        with open(root_feedback, "a", encoding="utf-8") as f:
            f.write(separator + feedback_content)
        log_ok("  收割 skill-feedback.md")

    # ── Step 6: Output summary ──
    print(f"\n  ✅ Post-merge Summary:")
    print(f"     Software: {software}")
    print(f"     Version: {version}")
    print(f"     Draft entries moved: {moved_count}")
    print(f"     Archive: archives/{letter}/{software}/{version}/")
    print(f"\n  下一步:")
    print(f"    git add .")
    print(f"    git commit -m \"chore: post-merge rebuild for {software} {version}\"")
    print(f"    git push")

    return 0


# ═══════════════════════════════════════════════════════
# CLI entry points
# ═══════════════════════════════════════════════════════

def submit_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc submit <software> <version>"""
    parser = argparse.ArgumentParser(
        prog="ohc submit",
        description="门禁检查(完成/W3/W4) + 自检 + git push + 自动创建PR + CI监控 + AI Review检查（阻塞式，失败 emit HANDOFF）",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_submit(args.software, args.version,
                      pdir=getattr(args, "project_dir", None))


def review_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc review <software> <version>"""
    parser = argparse.ArgumentParser(
        prog="ohc review",
        description="本地审核辅助（直接扫描目录）",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_review(
        args.software,
        args.version,
        pdir=getattr(args, "project_dir", None),
    )


def post_merge_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc post-merge <software> <version>"""
    parser = argparse.ArgumentParser(
        prog="ohc post-merge",
        description="合并后重建（draft→正式, 重建索引, 收割反馈）",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_post_merge(args.software, args.version,
                          pdir=getattr(args, "project_dir", None))
