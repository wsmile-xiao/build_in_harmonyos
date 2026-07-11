"""W1-W4 workflow enforcement checks.

Implements the 4 mandatory workflow rules defined in SKILL.md §0.2:
  W1 — Sync main before adaptation
  W2 — PR atomicity (one recipe per PR, framework changes separate)
  W3 — Local CI simulation before PR
  W4 — Knowledge graph completeness check
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


# ── W1: Git sync check ──

def check_git_sync(pdir: str | None = None, *, blocking: bool = False) -> int:
    """W1: Verify local main is up-to-date with remote.

    Returns 0 if synced (or no remote), 1 if behind, 2 if no git.
    When blocking=True, exits process if not synced.
    """
    project = Path(pdir) if pdir else Path(find_project_dir())
    git_dir = project / ".git"
    if not git_dir.exists():
        return 2  # No git repo, skip

    # Check if remote exists
    rc, out = _run(["git", "remote", "get-url", "origin"], cwd=str(project))
    if rc != 0:
        return 0  # No remote, skip

    log_info("W1: 检查主仓库同步状态...")

    # Fetch without merging
    rc, _ = _run(["git", "fetch", "origin", "main"], cwd=str(project))
    if rc != 0:
        log_warn("  git fetch 失败（网络问题？），跳过 W1 检查")
        return 0  # Don't block on network issues

    # Compare local vs remote
    rc, local = _run(["git", "rev-parse", "HEAD"], cwd=str(project))
    rc2, remote = _run(["git", "rev-parse", "origin/main"], cwd=str(project))

    local = local.strip()
    remote = remote.strip()

    if local == remote:
        log_ok("  ✅ 已是最新 (main 与 origin/main 一致)")
        return 0

    # Check if local is behind
    rc, behind = _run(["git", "rev-list", "--count", f"{local}..{remote}"], cwd=str(project))
    rc2, ahead = _run(["git", "rev-list", "--count", f"{remote}..{local}"], cwd=str(project))

    behind_n = int(behind.strip() or "0")
    ahead_n = int(ahead.strip() or "0")

    if behind_n > 0 and ahead_n == 0:
        log_fail(f"  ❌ 本地落后远端 {behind_n} 个提交！必须先同步:")
        log_fail(f"     git checkout main && git pull origin main")
        if blocking:
            sys.exit(1)
        return 1
    elif behind_n > 0 and ahead_n > 0:
        log_warn(f"  ⚠️ 本地领先 {ahead_n} / 落后 {behind_n} 个提交（分叉状态）")
        log_warn(f"     建议: git rebase origin/main 或 git merge origin/main")
        if blocking:
            sys.exit(1)
        return 1
    else:
        # ahead only — fine, on a feature branch
        log_ok(f"  ✅ 本地领先 {ahead_n} 个提交（功能分支状态）")
        return 0


# ── W2: PR atomicity check ──

_FRAMEWORK_PATHS = {
    "scripts/", "templates/", "ci/", "references/", "docs/",
    "SKILL.md", "README.md", "CONTRIBUTING.md", "KNOW_HOW_WHY.md",
    ".gitignore", "SUMMARY.md",
    "knowledge/graph/index.tsv", "knowledge/graph/principles.kv",
    "knowledge/graph/pre-scan-rules.yaml", "knowledge/graph/_template.kv",
    "knowledge/ARCHIVE-SPEC.md", "knowledge/operations/",
    "knowledge/error-patterns.md",
}

def check_pr_atomicity(pdir: str | None = None) -> int:
    """W2: Verify current changes only touch recipe files, not framework.

    Checks `git diff --name-only` against main for framework file changes.
    Returns 0 if clean, 1 if framework files modified.
    """
    project = Path(pdir) if pdir else Path(find_project_dir())
    if not (project / ".git").exists():
        return 0

    log_info("W2: 检查 PR 原子性（配方 vs 框架隔离）...")

    # Get changed files vs main
    rc, out = _run(["git", "diff", "--name-only", "origin/main...HEAD"], cwd=str(project))
    if rc != 0:
        # Fallback: use git status
        rc, out = _run(["git", "status", "--porcelain"], cwd=str(project))
        if rc != 0:
            return 0
        files = [line[3:].strip() for line in out.split("\n") if line.strip()]
    else:
        files = [f.strip() for f in out.split("\n") if f.strip()]

    if not files:
        log_ok("  ✅ 无变更文件")
        return 0

    framework_changes = []
    recipe_changes = []

    for f in files:
        # Check if it's a framework file
        is_framework = False
        for fw_path in _FRAMEWORK_PATHS:
            if f.startswith(fw_path) or f == fw_path:
                is_framework = True
                break
        # knowledge/graph/E*.kv and knowledge/doc/E*.md are recipe-level knowledge
        if f.startswith("knowledge/graph/E") or f.startswith("knowledge/doc/E"):
            is_framework = False

        if is_framework:
            framework_changes.append(f)
        else:
            recipe_changes.append(f)

    if framework_changes:
        log_fail(f"  ❌ 发现框架文件变更（应单独提交 PR）:")
        for f in framework_changes[:10]:
            log_fail(f"     {f}")
        if len(framework_changes) > 10:
            log_fail(f"     ... 还有 {len(framework_changes) - 10} 个")
        log_fail(f"  配方文件变更: {len(recipe_changes)} 个")
        log_fail(f"  ⚠️ 请将框架修改拆分到独立 PR，配方 PR 只包含 archives/ + knowledge/ 内容")
        return 1

    log_ok(f"  ✅ 仅含配方变更 ({len(recipe_changes)} 文件)，无框架文件")
    return 0


# ── W3: Local CI simulation ──

def run_local_ci(software: str, version: str, pdir: str | None = None) -> int:
    """W3: Run CI scripts locally before submitting PR.

    Executes ci/conan/setup.sh + ci/conan/build_and_test.sh.
    Returns 0 if pass, 1 if fail.
    """
    project = Path(pdir) if pdir else Path(find_project_dir())
    setup_sh = project / "ci" / "conan" "setup.sh"
    build_sh = project / "ci" / "conan" / "build_and_test.sh"

    if not build_sh.exists():
        log_warn("W3: ci/conan/build_and_test.sh 不存在，跳过本地 CI 模拟")
        return 0

    log_info(f"W3: 本地 CI 模拟验证 ({software}/{version})...")

    # Run setup.sh
    if setup_sh.exists():
        log_info("  [1/2] setup.sh...")
        rc, out = _run(["bash", str(setup_sh)], cwd=str(project), timeout=120)
        if rc != 0:
            log_fail(f"  ❌ setup.sh 失败 (RC={rc})")
            return 1
        log_ok("  ✅ setup.sh 通过")

    # Run build_and_test.sh
    log_info(f"  [2/2] build_and_test.sh {software}/{version}...")
    pkg_spec = f"archives/{software[0]}/{software}/{version}"
    rc, out = _run(
        ["zsh", str(build_sh), pkg_spec],
        cwd=str(project),
        env_extra={"CI_PACKAGES": pkg_spec, "CI_REPO_ROOT": str(project)},
        timeout=600,
    )
    if rc != 0:
        log_fail(f"  ❌ build_and_test.sh 失败 (RC={rc})")
        log_fail("  本地 CI 模拟未通过，不要提交 PR！")
        # Print last 20 lines of output for debugging
        if out:
            for line in out.split("\n")[-20:]:
                log_fail(f"    {line}")
        return 1

    log_ok("  ✅ 本地 CI 模拟通过")
    return 0


# ── W4: Knowledge graph completeness ──

_REQUIRED_KV_FIELDS = ["error_signature", "root_cause", "rec_approach"]

def check_knowledge_completeness(pdir: str | None = None) -> int:
    """W4: Check knowledge graph completeness and compliance.

    - doc/E###.md ↔ graph/E###.kv pairing
    - Required fields non-empty in each .kv
    - graph validate passes
    Returns 0 if pass, 1 if issues found.
    """
    project = Path(pdir) if pdir else Path(find_project_dir())
    graph_dir = project / "knowledge" / "graph"
    doc_dir = project / "knowledge" / "doc"

    log_info("W4: 知识图谱完整性检查...")

    issues = 0

    # 1. doc ↔ kv pairing
    kv_ids = set()
    if graph_dir.exists():
        for f in graph_dir.iterdir():
            if f.name.startswith("E") and f.suffix == ".kv" and f.name != "_template.kv":
                kv_ids.add(f.stem)

    doc_ids = set()
    if doc_dir.exists():
        for f in doc_dir.iterdir():
            if f.name.startswith("E") and f.suffix == ".md":
                doc_ids.add(f.stem)

    missing_docs = kv_ids - doc_ids
    orphan_docs = doc_ids - kv_ids

    if missing_docs:
        log_warn(f"  ⚠️ {len(missing_docs)} 个 KV 缺少配套 MD:")
        for eid in sorted(missing_docs)[:5]:
            log_warn(f"     {eid}.kv → 缺 {eid}.md")
        if len(missing_docs) > 5:
            log_warn(f"     ... 还有 {len(missing_docs) - 5} 个")
        issues += 1

    if orphan_docs:
        log_warn(f"  ⚠️ {len(orphan_docs)} 个 MD 无对应 KV:")
        for eid in sorted(orphan_docs)[:5]:
            log_warn(f"     {eid}.md → 无 {eid}.kv")
        issues += 1

    if not missing_docs and not orphan_docs:
        log_ok(f"  ✅ doc↔kv 配套完整 ({len(kv_ids)} 对)")

    # 2. Required fields check
    empty_fields = 0
    for eid in sorted(kv_ids):
        kv_path = graph_dir / f"{eid}.kv"
        content = kv_path.read_text(encoding="utf-8")
        fields = {}
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(\w+):\s*(.*)", line)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2).strip()

        for rf in _REQUIRED_KV_FIELDS:
            val = fields.get(rf, "")
            if not val or val.startswith("TODO") or val == "|":
                if empty_fields == 0:
                    log_warn(f"  ⚠️ 字段缺失:")
                log_warn(f"     {eid}.kv: {rf} 为空")
                empty_fields += 1

    if empty_fields == 0:
        log_ok(f"  ✅ 必填字段完整 ({len(_REQUIRED_KV_FIELDS)} 字段 × {len(kv_ids)} 条目)")
    else:
        issues += 1

    # 3. graph validate
    ohc_py = project / "scripts" / "ohc-run.py"
    if ohc_py.exists():
        rc, out = _run(
            ["python3", str(ohc_py), "graph", "validate"],
            cwd=str(project), timeout=30
        )
        if rc != 0:
            log_warn(f"  ⚠️ graph validate 报告问题")
            issues += 1
        else:
            log_ok("  ✅ graph validate 通过")

    # 4. Check drafts if any new ones exist
    drafts_dir = project / "knowledge" / "drafts"
    if drafts_dir.exists():
        drafts = list(drafts_dir.glob("DRAFT-*.kv"))
        if drafts:
            log_info(f"  📝 发现 {len(drafts)} 个草稿待审:")
            for d in drafts[:5]:
                log_info(f"     {d.name}")

    if issues > 0:
        log_fail(f"  ❌ 知识图谱完整性检查发现 {issues} 类问题")
        return 1

    log_ok("  ✅ 知识图谱完整性检查通过")
    return 0


# ── Helpers ──

def _run(cmd: list[str], *, cwd: str | None = None,
         env_extra: dict | None = None, timeout: int = 60) -> tuple[int, str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        result = subprocess.run(
            cmd, cwd=cwd, env=env,
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        return 1, "TIMEOUT"
    except FileNotFoundError:
        return 1, ""
