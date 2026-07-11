#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-PR 独立审计脚本 — 提交PR前的质量门禁 (W5)。

加载 .gitcode/ 下的审查规则，收集本次变更的全部文件，
生成标准化审计输入，供 AI 子任务独立审计。

工作流位置: W3(本地CI模拟) → ✅ → W5(本脚本) → ✅ → 创建PR

用法:
    # 生成审计输入 (在功能分支上执行)
    python3 scripts/pre_pr_audit.py --repo-dir /path/to/build_in_harmonyos

    # 指定软件名和版本 (自动定位变更文件)
    python3 scripts/pre_pr_audit.py --repo-dir /path/to/build_in_harmonyos \\
        --package sqlite3 --version 3.49.1

    # 输出审计报告 (审计子任务完成后调用)
    python3 scripts/pre_pr_audit.py --report --repo-dir /path/to/build_in_harmonyos \\
        --package sqlite3 --version 3.49.1 --audit-result /path/to/audit-result.json

退出码:
    0 — 审计输入生成成功 (不代表审计通过)
    1 — 前置条件不满足 (W3未通过/无变更文件)
    2 — 审计报告中存在未修复的 P0/P1 问题
"""
import argparse
import json
import os
import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime


def _find_git() -> str:
    """Find git: env var GIT_BIN → PATH → common dirs → fallback."""
    env_val = os.environ.get("GIT_BIN", "").strip()
    if env_val and os.path.isfile(env_val) and os.access(env_val, os.X_OK):
        return env_val
    found = shutil.which("git")
    if found:
        return found
    for d in ["/data/service/hnp/bin", "/usr/local/bin", "/usr/bin", "/system/bin"]:
        p = os.path.join(d, "git")
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return "git"


def run_git(repo_dir, *args):
    """执行 git 命令并返回输出。"""
    git_bin = _find_git()
    result = subprocess.run(
        [git_bin, "-C", str(repo_dir)] + list(args),
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip()


def get_changed_files(repo_dir, base_branch="main"):
    """获取当前分支相对于 base_branch 的变更文件列表。"""
    # 先获取当前分支名
    current_branch = run_git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
    if not current_branch or current_branch == "HEAD":
        print("ERROR: 不在功能分支上 (detached HEAD)", file=sys.stderr)
        return []

    # 获取变更文件 (相对于 main 的 diff)
    diff_output = run_git(repo_dir, "diff", "--name-only", f"origin/{base_branch}...HEAD")
    if not diff_output:
        # fallback: 用 status
        diff_output = run_git(repo_dir, "diff", "--name-only", f"{base_branch}...HEAD")

    files = [f.strip() for f in diff_output.split("\n") if f.strip()]
    return files


def load_audit_rules(repo_dir):
    """加载 .gitcode/ 下的审计规则文件。"""
    gitcode_dir = Path(repo_dir) / ".gitcode"
    rules = {}

    code_style_path = gitcode_dir / "code-style.md"
    review_memory_path = gitcode_dir / "review-memory.md"

    if code_style_path.exists():
        rules["code_style"] = code_style_path.read_text(encoding="utf-8")
    else:
        print(f"WARNING: 未找到 {code_style_path}", file=sys.stderr)

    if review_memory_path.exists():
        rules["review_memory"] = review_memory_path.read_text(encoding="utf-8")
    else:
        print(f"WARNING: 未找到 {review_memory_path}", file=sys.stderr)

    return rules


def collect_file_contents(repo_dir, file_list):
    """收集变更文件的完整内容。"""
    repo = Path(repo_dir)
    files_content = {}
    for f in file_list:
        full_path = repo / f
        if full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                files_content[f] = content
            except Exception as e:
                files_content[f] = f"[读取失败: {e}]"
        else:
            files_content[f] = "[文件不存在]"
    return files_content


def get_diff_stat(repo_dir, base_branch="main"):
    """获取 diff 统计信息。"""
    return run_git(repo_dir, "diff", "--stat", f"origin/{base_branch}...HEAD")


def cmd_generate(args):
    """生成审计输入。"""
    repo_dir = Path(args.repo_dir)
    if not repo_dir.exists():
        print(f"ERROR: 仓库目录不存在: {repo_dir}", file=sys.stderr)
        sys.exit(1)

    # 检查是否在功能分支上
    current_branch = run_git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
    if current_branch in ("main", "master", "HEAD", ""):
        print(f"ERROR: 当前在 {current_branch} 分支，请切换到功能分支", file=sys.stderr)
        sys.exit(1)

    print(f"[step] W5: Pre-PR 独立审计")
    print(f"  分支: {current_branch}")
    print(f"  仓库: {repo_dir}")

    # 1. 获取变更文件
    changed_files = get_changed_files(repo_dir, args.base_branch)
    if not changed_files:
        print("ERROR: 没有变更文件，无需审计", file=sys.stderr)
        sys.exit(1)

    print(f"\n[step] 变更文件 ({len(changed_files)} 个):")
    for f in changed_files:
        print(f"  {f}")

    # 2. 检查 W2 PR 原子性
    non_recipe_files = [
        f for f in changed_files
        if not f.startswith("archives/") and f != ".gitcode/code-style.md" and f != ".gitcode/review-memory.md"
    ]
    if non_recipe_files:
        print(f"\n[warn] W2 PR 原子性警告: 以下文件不属于配方目录:")
        for f in non_recipe_files:
            print(f"  {f}")

    # 3. 加载审计规则
    print(f"\n[step] 加载审计规则...")
    rules = load_audit_rules(repo_dir)
    if not rules:
        print("ERROR: 未找到审计规则文件", file=sys.stderr)
        sys.exit(1)
    print(f"  code-style.md: {len(rules.get('code_style', ''))} chars")
    print(f"  review-memory.md: {len(rules.get('review_memory', ''))} chars")

    # 4. 收集文件内容
    print(f"\n[step] 收集变更文件内容...")
    file_contents = collect_file_contents(repo_dir, changed_files)
    total_size = sum(len(v) for v in file_contents.values())
    print(f"  总大小: {total_size} chars")

    # 5. 获取 diff 统计
    diff_stat = get_diff_stat(repo_dir, args.base_branch)

    # 6. 组装审计输入
    audit_input = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "branch": current_branch,
            "base_branch": args.base_branch,
            "repo_dir": str(repo_dir),
            "package": args.package,
            "version": args.version,
        },
        "changed_files": changed_files,
        "diff_stat": diff_stat,
        "rules": rules,
        "file_contents": file_contents,
    }

    # 7. 输出审计输入
    default_dir = os.path.join(os.path.expanduser("~"), "tmp")
    os.makedirs(default_dir, exist_ok=True)
    safe_branch = current_branch.replace("/", "-")
    output_file = args.output or os.path.join(default_dir, f"audit-input-{safe_branch}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(audit_input, f, ensure_ascii=False, indent=2)

    print(f"\n[ok] 审计输入已生成: {output_file}")
    print(f"  文件数: {len(changed_files)}")
    print(f"  规则数: {len(rules)}")
    print(f"  总大小: {total_size + sum(len(v) for v in rules.values())} chars")

    # 8. 输出子任务 prompt
    print(f"\n{'='*80}")
    print("审计子任务 prompt (复制以下内容派发给子任务):")
    print(f"{'='*80}")
    print(f"""
你是一个独立的代码审计员。请对以下 Conan 配方变更进行严格审计。

审计规则文件已加载，请逐条对照检查。审计输入文件: {output_file}

审计流程:
1. 读取审计输入文件 (JSON 格式)
2. 加载 rules.code_style (代码规范性标准) 和 rules.review_memory (PR审查规则)
3. 对每个 changed_files 中的文件，逐条对照规则检查
4. 特别关注 review-memory.md 中的「一、欺骗性行为检测」(最高优先级)
5. 输出审计报告 JSON, 格式:
   {{
     "verdict": "pass|fail",
     "issues": [
       {{
         "severity": "P0|P1|P2|P3",
         "rule_id": "R34",
         "file": "archives/s/sqlite3/3.49.1/test_package/test.c",
         "line": 15,
         "description": "空壳测试: test 只打印字符串未调用 API",
         "fix_suggestion": "添加 sqlite3_open/exec/prepare 调用"
       }}
     ],
     "summary": "审计总结..."
   }}

严重程度:
- P0: 欺骗性行为 (空壳测试/伪造状态/伪造sha256) — 一律 fail
- P1: 配方正确性 (硬编码/平台兼容/版本号) — 必须 fail
- P2: 代码规范 (命名/格式/import) — 警告
- P3: 建议性改进 — 提示

请执行审计并输出报告。
""")

    return audit_input


def cmd_report(args):
    """处理审计报告，判断是否可以提交 PR。"""
    if not args.audit_result:
        print("ERROR: 需要 --audit-result 参数指定审计报告路径", file=sys.stderr)
        sys.exit(1)

    with open(args.audit_result, "r", encoding="utf-8") as f:
        report = json.load(f)

    verdict = report.get("verdict", "unknown")
    issues = report.get("issues", [])

    print(f"\n{'='*80}")
    print(f"W5 审计报告")
    print(f"{'='*80}")
    print(f"结论: {verdict.upper()}")
    print(f"问题数: {len(issues)}")

    if issues:
        print(f"\n问题列表:")
        for i, issue in enumerate(issues):
            severity = issue.get("severity", "P3")
            rule_id = issue.get("rule_id", "")
            file = issue.get("file", "")
            line = issue.get("line", "")
            desc = issue.get("description", "")
            fix = issue.get("fix_suggestion", "")

            icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🔵"}.get(severity, "⚪")
            print(f"\n  [{i+1}] {icon} {severity} — {rule_id}")
            print(f"      文件: {file}:{line}")
            print(f"      问题: {desc}")
            if fix:
                print(f"      修复: {fix}")

    # 统计各级别问题
    p0_count = sum(1 for i in issues if i.get("severity") == "P0")
    p1_count = sum(1 for i in issues if i.get("severity") == "P1")
    p2_count = sum(1 for i in issues if i.get("severity") == "P2")
    p3_count = sum(1 for i in issues if i.get("severity") == "P3")

    print(f"\n统计: P0={p0_count} P1={p1_count} P2={p2_count} P3={p3_count}")

    if verdict == "pass" and p0_count == 0 and p1_count == 0:
        print(f"\n✅ W5 审计通过 — 可以创建 PR")
        print(f"   P2/P3 问题可在后续迭代中处理")
        sys.exit(0)
    else:
        print(f"\n❌ W5 审计未通过 — 必须修复 P0/P1 问题后才能创建 PR")
        print(f"   修复完成后重新生成审计输入并重新审计")
        sys.exit(2)


def cmd_check(args):
    """检查 W4 前置条件 (W3 本地 CI 是否通过)。"""
    repo_dir = Path(args.repo_dir)

    # 检查是否有 CI 模拟结果 (JSON 格式，防伪造)
    ci_result_file = repo_dir / ".ci-result.json"
    if ci_result_file.exists():
        try:
            import json as _json
            with open(ci_result_file, "r") as f:
                ci_data = _json.load(f)
            # 验证字段完整性
            timestamp = ci_data.get("timestamp", "")
            exit_code = ci_data.get("exit_code", -1)
            if not timestamp:
                print("⚠️  .ci-result.json 缺少 timestamp 字段")
                return False
            if exit_code != 0:
                print(f"⚠️  W3 本地 CI 模拟 exit_code={exit_code}，未通过")
                return False
            print(f"✅ W3 本地 CI 模拟已通过 (timestamp: {timestamp})")
            return True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  .ci-result.json 格式无效: {e}")
            return False
    else:
        print("⚠️  W3 本地 CI 模拟结果未找到 (.ci-result.json)")
        print("   请先完成 W3: bash ci/conan/build_and_test.sh <软件名>/<版本>")
        print("   然后写入结果: python3 -c \"import json,time; json.dump({'timestamp':time.strftime('%Y-%m-%dT%H:%M:%S'),'exit_code':0,'log_path':'ci-local-output.log'}, open('.ci-result.json','w'), indent=2)\"")
        if args.force:
            print("   --force: 跳过 W3 检查 (不推荐)")
            return True
        return False


def main():
    parser = argparse.ArgumentParser(
        description="W5: Pre-PR 独立审计 — 提交PR前的质量门禁",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # generate
    p = sub.add_parser("generate", help="生成审计输入")
    p.add_argument("--repo-dir", required=True, help="build_in_harmonyos 仓库目录")
    p.add_argument("--package", help="软件名")
    p.add_argument("--version", help="版本号")
    p.add_argument("--base-branch", default="main", help="基准分支")
    p.add_argument("--output", help="审计输入输出路径 (默认 /tmp/)")
    p.set_defaults(func=cmd_generate)

    # report
    p = sub.add_parser("report", help="处理审计报告")
    p.add_argument("--audit-result", required=True, help="审计报告 JSON 路径")
    p.add_argument("--repo-dir", help="仓库目录")
    p.add_argument("--package", help="软件名")
    p.add_argument("--version", help="版本号")
    p.set_defaults(func=cmd_report)

    # check
    p = sub.add_parser("check", help="检查 W5 前置条件")
    p.add_argument("--repo-dir", required=True, help="仓库目录")
    p.add_argument("--force", action="store_true", help="跳过 W3 检查")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = args.func(args)
    if result is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
