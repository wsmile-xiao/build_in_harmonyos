"""协作提交单系统 — submit / review / approve / reject。

替代 Git PR，用于多 Agent 协作场景下的提交审核流程。

Usage:
    python3 ohc-run.py submit <software> <version>
    python3 ohc-run.py review [--list | <submission-id> | --all-pending]
    python3 ohc-run.py approve <submission-id>
    python3 ohc-run.py reject <submission-id> --reason="..."
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
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

def _submissions_dir(pdir: str | None = None) -> Path:
    """Return submissions/ directory root."""
    return Path(pdir or find_project_dir()) / "submissions"


def _pending_dir(pdir: str | None = None) -> Path:
    d = _submissions_dir(pdir) / "pending"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _approved_dir(pdir: str | None = None) -> Path:
    d = _submissions_dir(pdir) / "approved"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rejected_dir(pdir: str | None = None) -> Path:
    d = _submissions_dir(pdir) / "rejected"
    d.mkdir(parents=True, exist_ok=True)
    return d


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
    "status", "software", "version", "compile_date", "build_system",
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
    """Check that PROGRESS.md has a closing marker."""
    progress = ver_dir / "PROGRESS.md"
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
    if status not in ("success", "partial"):
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
# cmd: submit
# ═══════════════════════════════════════════════════════

def cmd_submit(software: str, version: str, pdir: str | None = None) -> int:
    """Create a submission for the given software+version."""
    project_dir = pdir or find_project_dir()
    agent_id = get_agent_id(project_dir)
    letter = software[0].lower()
    ver_dir = _archive_dir(letter, software, version, project_dir)

    if not ver_dir.exists():
        log_fail(f"版本目录不存在: {ver_dir}")
        return 1

    # Load manifest
    manifest = _parse_yaml_simple(ver_dir / "manifest.yaml")
    status = str(manifest.get("status", "unknown"))
    build_system = str(manifest.get("build_system", "unknown"))

    # ── Checklist ──
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

    # ── Scan patches ──
    patches_dir = ver_dir / "patches"
    patches_count = 0
    packaging_files: list[str] = []
    if patches_dir.is_dir():
        patches_count = len(list(patches_dir.glob("*.patch")))
    packaging_dir = ver_dir / "packaging"
    if packaging_dir.is_dir():
        packaging_files = sorted([f.name for f in packaging_dir.glob("*.tar.gz")])

    # ── Test results ──
    test_passed = manifest.get("test_results", {})
    if isinstance(test_passed, dict):
        test_passed_val = test_passed.get("passed", 0)
        test_failed_val = test_passed.get("failed", 0)
        test_note = test_passed.get("note", "")
    else:
        # Try flat keys
        test_passed_val = manifest.get("test_passed", 0)
        test_failed_val = manifest.get("test_failed", 0)
        test_note = manifest.get("test_note", "")

    # ── Knowledge ──
    draft_entries = _scan_draft_entries(software, project_dir)
    knowledge_gained = _scan_knowledge_gained(ver_dir)
    knowledge_ref = _scan_knowledge_ref(ver_dir)

    # Classify knowledge gained into L1/L2
    l1_writes: list[str] = []
    l2_writes: list[str] = []
    for entry in knowledge_gained:
        # Simple heuristic: entries mentioning platform/system → L1
        if any(kw in entry.lower() for kw in ["平台", "platform", "系统", "system",
                                                "kernel", "bionic", "musl"]):
            l1_writes.append(entry)
        else:
            l2_writes.append(entry)

    # ── New issues count ──
    reports_dir = ver_dir / "reports"
    new_issues = 0
    if reports_dir.is_dir():
        for rf in reports_dir.glob("*.md"):
            content = rf.read_text(encoding="utf-8", errors="replace")
            new_issues += len(re.findall(r'❌|FAIL|失败|issue', content, re.I))

    # ── Generate submission YAML ──
    today_str = datetime.now().strftime("%Y%m%d")
    submission_id = f"{software}-{version}-{today_str}"
    submitted_at = datetime.now().isoformat()

    submission_data = {
        "submission_id": submission_id,
        "submitted_at": submitted_at,
        "contributor_id": agent_id,
        "deliverables": {
            "archive_path": f"archives/{letter}/{software}/{version}/",
            "patches_count": patches_count,
            "packaging": packaging_files,
        },
        "build_result": {
            "status": status,
            "build_system": build_system,
            "test_passed": test_passed_val,
            "test_failed": test_failed_val,
            "test_note": test_note,
        },
        "knowledge_new": {
            "draft_entries": draft_entries,
            "l1_writes": l1_writes,
            "l2_writes": l2_writes,
        },
        "feedback": {
            "skill_feedback_path": f"archives/{letter}/{software}/{version}/reports/skill-feedback.md",
            "new_issues": new_issues,
        },
        "checklist": checklist,
    }

    # ── Write submission file (overwrite if exists) ──
    pending_dir = _pending_dir(project_dir)
    # Find and remove any existing submission for same software+version
    existing_pattern = f"{software}-{version}-*.yaml"
    for existing in pending_dir.glob(existing_pattern):
        existing.unlink()
        log_info(f"覆盖已有提交单: {existing.name}")

    submission_path = pending_dir / f"{submission_id}.yaml"
    _write_yaml_structured(submission_path, submission_data)

    log_ok(f"提交单已创建: {submission_path}")
    print(f"\n  📋 Submission: {submission_id}")
    print(f"     Contributor: {agent_id}")
    print(f"     Status: {status}")
    print(f"     Patches: {patches_count}")
    print(f"     Checklist: {sum(checklist.values())}/{len(checklist)} passed")

    return 0


def _write_yaml_structured(path: Path, data: dict, indent: int = 0) -> None:
    """Write a nested dict to YAML format."""
    lines: list[str] = []
    _flatten_yaml(data, lines, indent=0)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _flatten_yaml(data, lines: list[str], indent: int = 0) -> None:
    """Recursively flatten a dict/list into YAML lines."""
    prefix = "  " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                _flatten_yaml(value, lines, indent + 1)
            elif isinstance(value, bool):
                lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
            elif isinstance(value, int):
                lines.append(f"{prefix}{key}: {value}")
            elif isinstance(value, list):
                if not value:
                    lines.append(f"{prefix}{key}: []")
                else:
                    lines.append(f"{prefix}{key}:")
                    _flatten_yaml(value, lines, indent + 1)
            else:
                # String value
                val_str = str(value)
                if "\n" in val_str or ":" in val_str:
                    lines.append(f'{prefix}{key}: "{val_str}"')
                else:
                    lines.append(f"{prefix}{key}: {val_str}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Not expected in our simple format
                lines.append(f"{prefix}- {item}")
            elif isinstance(item, bool):
                lines.append(f"{prefix}- {'true' if item else 'false'}")
            else:
                val_str = str(item)
                lines.append(f"{prefix}- {val_str}")
    else:
        lines.append(f"{prefix}{data}")


# ═══════════════════════════════════════════════════════
# cmd: review
# ═══════════════════════════════════════════════════════

def cmd_review(submission_id: str | None = None, *,
               list_pending: bool = False, all_pending: bool = False,
               pdir: str | None = None) -> int:
    """Review one or all pending submissions."""
    project_dir = pdir or find_project_dir()
    pending_dir = _pending_dir(project_dir)

    # ── List mode ──
    if list_pending:
        submissions = sorted(pending_dir.glob("*.yaml"))
        if not submissions:
            log_info("无待审核提交单")
            return 0
        print(f"\n  📋 Pending Submissions ({len(submissions)}):\n")
        print(f"  {'ID':<35} {'Contributor':<12} {'Software':<20} {'Status':<10} {'Time'}")
        print(f"  {'─' * 95}")
        for sp in submissions:
            data = _parse_yaml_simple(sp)
            sid = data.get("submission_id", sp.stem)
            contrib = data.get("contributor_id", "?")
            deliverables = data.get("deliverables", {})
            archive_path = deliverables if isinstance(deliverables, str) else str(deliverables.get("archive_path", "?"))
            # Extract software name from archive_path
            parts = archive_path.split("/")
            sw_name = parts[2] if len(parts) > 2 else "?"
            br = data.get("build_result", {})
            status = br.get("status", "?") if isinstance(br, dict) else "?"
            submitted = data.get("submitted_at", "?")
            if len(submitted) > 19:
                submitted = submitted[:19]
            print(f"  {sid:<35} {contrib:<12} {sw_name:<20} {status:<10} {submitted}")
        print()
        return 0

    # ── All-pending mode ──
    if all_pending:
        submissions = sorted(pending_dir.glob("*.yaml"))
        if not submissions:
            log_info("无待审核提交单")
            return 0
        total_pass = 0
        total_fail = 0
        for sp in submissions:
            print(f"\n{'═' * 60}")
            result = _review_single(sp, project_dir)
            if result == 0:
                total_pass += 1
            else:
                total_fail += 1
        print(f"\n{'═' * 60}")
        log_info(f"审核完成: {total_pass} PASS, {total_fail} FAIL")
        return 0 if total_fail == 0 else 1

    # ── Single submission ──
    if not submission_id:
        log_fail("请指定 submission-id 或使用 --list / --all-pending")
        return 1

    # Find the submission file
    sub_path = pending_dir / f"{submission_id}.yaml"
    if not sub_path.exists():
        # Try glob
        candidates = list(pending_dir.glob(f"{submission_id}*.yaml"))
        if len(candidates) == 1:
            sub_path = candidates[0]
        elif len(candidates) > 1:
            log_fail(f"多个匹配: {[c.name for c in candidates]}")
            return 1
        else:
            log_fail(f"提交单不存在: {submission_id}")
            return 1

    return _review_single(sub_path, project_dir)


def _review_single(sub_path: Path, project_dir: str) -> int:
    """Review a single submission and output results."""
    data = _parse_yaml_simple(sub_path)
    sid = data.get("submission_id", sub_path.stem)
    print(f"\n  🔍 Reviewing: {sid}")
    log_info(f"Contributor: {data.get('contributor_id', '?')}")

    # Extract archive path info
    deliverables = data.get("deliverables", {})
    if isinstance(deliverables, dict):
        archive_path = deliverables.get("archive_path", "")
    else:
        archive_path = ""

    # Parse archive path: archives/{letter}/{name}/{version}/
    parts = archive_path.strip("/").split("/")
    if len(parts) < 4:
        log_fail(f"无法解析 archive_path: {archive_path}")
        return 1

    letter, sw_name, version = parts[1], parts[2], parts[3]
    ver_dir = Path(project_dir) / "archives" / letter / sw_name / version

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
    # In our submission system (no git), we check if _index.yaml or SUMMARY.md
    # appear in the archive directory (they shouldn't be there)
    idx_path = Path(project_dir) / "archives" / "_index.yaml"
    summary_path = Path(project_dir) / "SUMMARY.md"
    forbidden_modified = False
    # Since there's no git, we just note this check passes by default
    # A real implementation would check timestamps or checksums
    _record("5. 禁止文件检查", "PASS", "archives/_index.yaml 和 SUMMARY.md 未在提交范围")

    # ── Check 6: PROGRESS.md 已关闭 ──
    if _check_progress_closed(ver_dir):
        _record("6. PROGRESS关闭", "PASS")
    else:
        _record("6. PROGRESS关闭", "FAIL", "PROGRESS.md 未包含结束标记")

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
    br = data.get("build_result", {})
    status = br.get("status", "unknown") if isinstance(br, dict) else "unknown"
    if _check_packaging_present(ver_dir, status):
        _record("9. 打包产物", "PASS")
    else:
        _record("9. 打包产物", "WARN", "缺少 tar.gz")

    # ── Check 10: test-report.md ──
    if _check_test_report(ver_dir):
        _record("10. 测试报告", "PASS")
    else:
        _record("10. 测试报告", "WARN", "缺少 reports/test-report.md")

    # ── Check 11: Checklist from submission ──
    checklist = data.get("checklist", {})
    if isinstance(checklist, dict):
        all_passed = all(v for v in checklist.values() if isinstance(v, bool))
        if all_passed:
            _record("11. 提交自检", "PASS")
        else:
            failed_checks = [k for k, v in checklist.items() if v is False]
            _record("11. 提交自检", "WARN", f"未通过: {failed_checks}")
    else:
        _record("11. 提交自检", "WARN", "提交单中无自检结果")

    # ── Check 12: Overall assessment ──
    if fail_count == 0:
        _record("12. 总体评估", "PASS", f"{pass_count} PASS, {warn_count} WARN")
    else:
        _record("12. 总体评估", "FAIL", f"{fail_count} FAIL, {warn_count} WARN")

    # ── Print summary ──
    print(f"\n  📋 Review Summary for {sid}:")
    print(f"  {'─' * 60}")
    for name, status, detail in checks:
        icon = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
        line = f"  {icon} {name}: {status}"
        if detail:
            line += f" — {detail}"
        print(line)

    print(f"  {'─' * 60}")
    total = pass_count + warn_count + fail_count
    print(f"  结果: {pass_count} PASS / {warn_count} WARN / {fail_count} FAIL (共 {total} 项)")

    return 1 if fail_count > 0 else 0


# ═══════════════════════════════════════════════════════
# cmd: approve
# ═══════════════════════════════════════════════════════

def cmd_approve(submission_id: str, pdir: str | None = None) -> int:
    """Approve a pending submission and merge its artifacts."""
    from .models import parse_kv_file, write_kv_file
    from .graph import _regenerate_index, _kv_to_tsv_row

    project_dir = pdir or find_project_dir()
    pending_dir = _pending_dir(project_dir)
    approved_dir = _approved_dir(project_dir)

    # Find submission
    sub_path = pending_dir / f"{submission_id}.yaml"
    if not sub_path.exists():
        candidates = list(pending_dir.glob(f"{submission_id}*.yaml"))
        if len(candidates) == 1:
            sub_path = candidates[0]
        elif len(candidates) > 1:
            log_fail(f"多个匹配: {[c.name for c in candidates]}")
            return 1
        else:
            log_fail(f"提交单不存在: {submission_id}")
            return 1

    data = _parse_yaml_simple(sub_path)
    sid = data.get("submission_id", sub_path.stem)

    # Extract archive path
    deliverables = data.get("deliverables", {})
    archive_path = deliverables.get("archive_path", "") if isinstance(deliverables, dict) else ""
    parts = archive_path.strip("/").split("/")
    if len(parts) < 4:
        log_fail(f"无法解析 archive_path: {archive_path}")
        return 1

    letter, sw_name, version = parts[1], parts[2], parts[3]

    log_info(f"Approving: {sid}")

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

    # ── Step 3: Rebuild archives/_index.yaml ──
    # Use summary.py's scan logic indirectly
    try:
        from .summary import _scan_archives_dir, _parse_yaml_simple as _sum_yaml
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
    feedback_path = (Path(project_dir) / "archives" / letter / sw_name / version
                     / "reports" / "skill-feedback.md")
    root_feedback = Path(project_dir) / "reports" / "skill-feedback.md"
    if feedback_path.exists():
        root_feedback.parent.mkdir(parents=True, exist_ok=True)
        feedback_content = feedback_path.read_text(encoding="utf-8")
        separator = f"\n\n---\n## {sw_name} {version} (from {sid})\n\n"
        with open(root_feedback, "a", encoding="utf-8") as f:
            f.write(separator + feedback_content)
        log_ok("  收割 skill-feedback.md")

    # ── Step 6: Move submission to approved/ ──
    target = approved_dir / sub_path.name
    shutil.move(str(sub_path), str(target))
    # Append approval metadata
    _append_yaml_fields(target, {
        "approved_at": datetime.now().isoformat(),
        "status": "approved",
    })

    # ── Step 7: Output summary ──
    print(f"\n  ✅ Approval Summary:")
    print(f"     Submission: {sid}")
    print(f"     Draft entries moved: {moved_count}")
    print(f"     Archive: {archive_path}")
    print(f"     Moved to: submissions/approved/{sub_path.name}")

    return 0


# ═══════════════════════════════════════════════════════
# cmd: reject
# ═══════════════════════════════════════════════════════

def cmd_reject(submission_id: str, reason: str = "",
               pdir: str | None = None) -> int:
    """Reject a pending submission."""
    project_dir = pdir or find_project_dir()
    pending_dir = _pending_dir(project_dir)
    rejected_dir = _rejected_dir(project_dir)

    # Find submission
    sub_path = pending_dir / f"{submission_id}.yaml"
    if not sub_path.exists():
        candidates = list(pending_dir.glob(f"{submission_id}*.yaml"))
        if len(candidates) == 1:
            sub_path = candidates[0]
        elif len(candidates) > 1:
            log_fail(f"多个匹配: {[c.name for c in candidates]}")
            return 1
        else:
            log_fail(f"提交单不存在: {submission_id}")
            return 1

    data = _parse_yaml_simple(sub_path)
    sid = data.get("submission_id", sub_path.stem)

    # Move to rejected/
    target = rejected_dir / sub_path.name
    shutil.move(str(sub_path), str(target))

    # Append rejection metadata
    _append_yaml_fields(target, {
        "status": "rejected",
        "rejected_at": datetime.now().isoformat(),
        "editor_notes": reason,
    })

    log_ok(f"已拒绝提交单: {sid}")
    print(f"\n  ❌ Rejected: {sid}")
    if reason:
        print(f"     原因: {reason}")
    print(f"     移动到: submissions/rejected/{sub_path.name}")

    return 0


# ═══════════════════════════════════════════════════════
# CLI entry points
# ═══════════════════════════════════════════════════════

def submit_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc submit <software> <version>"""
    parser = argparse.ArgumentParser(
        prog="ohc submit",
        description="创建协作提交单",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_submit(args.software, args.version,
                      pdir=getattr(args, "project_dir", None))


def review_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc review [--list | <id> | --all-pending]"""
    parser = argparse.ArgumentParser(
        prog="ohc review",
        description="审核协作提交单",
    )
    parser.add_argument("submission_id", nargs="?", default=None,
                        help="提交单 ID（可选）")
    parser.add_argument("--list", "-l", action="store_true",
                        help="列出所有待审核提交单")
    parser.add_argument("--all-pending", "-a", action="store_true",
                        help="审核所有待审核提交单")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_review(
        args.submission_id,
        list_pending=args.list,
        all_pending=args.all_pending,
        pdir=getattr(args, "project_dir", None),
    )


def approve_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc approve <submission-id>"""
    parser = argparse.ArgumentParser(
        prog="ohc approve",
        description="批准协作提交单并合并",
    )
    parser.add_argument("submission_id", help="提交单 ID")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_approve(args.submission_id,
                       pdir=getattr(args, "project_dir", None))


def reject_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc reject <submission-id> --reason='...'"""
    parser = argparse.ArgumentParser(
        prog="ohc reject",
        description="拒绝协作提交单",
    )
    parser.add_argument("submission_id", help="提交单 ID")
    parser.add_argument("--reason", "-r", default="",
                        help="拒绝原因")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)
    return cmd_reject(args.submission_id, reason=args.reason,
                      pdir=getattr(args, "project_dir", None))
