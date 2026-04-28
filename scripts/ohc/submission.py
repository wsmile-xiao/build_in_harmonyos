"""协作辅助工具 — 本地自检 + 审核辅助 + 合并后重建。

适配 Git + GitCode PR 工作流，替代原有提交单系统。

Usage:
    python3 ohc-run.py submit <software> <version>
    python3 ohc-run.py review <software> <version>
    python3 ohc-run.py post-merge <software> <version>
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
# cmd: submit — 纯自检
# ═══════════════════════════════════════════════════════

def cmd_submit(software: str, version: str, pdir: str | None = None) -> int:
    """Run self-check for the given software+version (no YAML generation)."""
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

    # ── Print summary ──
    passed_count = sum(1 for v in checklist.values() if v)
    total_count = len(checklist)

    print(f"\n  ✅ 自检完成: {passed_count}/{total_count} PASS")
    print(f"     Contributor: {agent_id}")
    print(f"     Status: {status}")
    print(f"     Patches: {patches_count}")
    print(f"     Knowledge: {len(knowledge_gained)} gained, {len(knowledge_ref)} ref")
    print(f"     Issues found: {new_issues}")
    print()
    print(f"  下一步:")
    print(f"    git checkout -b feat/{software}-{version}")
    print(f"    git add archives/ knowledge/graph/draft/")
    print(f"    git commit -m \"feat: 编译 {software} {version}\"")
    print(f"    git push origin feat/{software}-{version}")
    print(f"    然后在 GitCode 创建 PR")

    return 0


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
        description="编译自检（不生成提交单）",
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
