"""Unified CLI entry point for ohc."""
from __future__ import annotations
import sys

_MODULES = {
    "engine": "engine", "status": "status", "handoff": "handoff",
    "graph": "graph", "finish": "finish", "build": "driver",
    "init-build": "init_build",
    "check-env": "check_env", "init-archive": "init_archive",
    "check-knowledge-gap": "check_knowledge_gap",
    "close-archive": "close_archive", "search-url": "search_url",
    "refresh-patch": "refresh_patch", "finalize-archive": "finalize_archive",
    "verify-build": "verify_build",
    "summary": "summary",
    "submit": "submission",
    "review": "submission",
    "post-merge": "submission",
    "feedback": "feedback",
    "resolve-deps": "dependency_resolver",
    "track-edit": "edit_tracker",
    "dispatch": "dispatch",
    "clean-verify": "clean_verify",
    # v3.0: Conan recipe generation + verification
    "conan-init": "conan_recipe",
    "conan-verify": "conan_verify",
    "conan-migrate": "conan_recipe",
    # v8.6: Pre-analysis + Requirements graph
    "pre-analysis": "pre_analysis",
    "req": "requirements",
    # RESULT Step: 任务终态 result.json 上报（SKILL_RESULT_PROTOCOL_SPEC）
    "result": "result_report",
    # v12.13: 协议 v0.8 附录 D 语言预检（checkout 后、适配主流程前）
    "lang-preflight": "lang_detect",
    # v12.15: 预算检查（反馈 0831 P0-1: 长阶段前调用，耗尽自动写 timeout 终态）
    "budget-check": "budget",
    # v12.3: CI/W3 构建超时配置管理（ci/config/build_timeouts.txt）
    "timeout": "build_timeout",
    # v12.4: 草稿预审辅助（相似度证据 + 三态建议；纳入决策权在人工审核）
    "draft-review": "draft_review",
    # v12.5: 预编译源码风险扫描独立命令（规则集 + 知识库动态派生规则）
    "prescan": "pre_scan",
    # v12.6: 配方首稿检索（成长型语料：主仓配方 + 社区成功配方经 git 汇聚）
    "recipe-search": "recipe_search",
    # v12.6: 知识库质量月报（本地聚合，git 同步社区汇聚）
    "kb-report": "kb_report",
    # v12.6: 核心模块一键冒烟测试
    "selftest": "selftest",
}


def main() -> int:
    if len(sys.argv) < 2:
        _print_help()
        return 0
    command = sys.argv[1]
    sub_argv = sys.argv[2:]
    _warn_project_dir_mismatch()
    if command in _MODULES:
        mod = __import__(f"ohc.{_MODULES[command]}", fromlist=[_MODULES[command]])
        # 查找 {command}_cli 函数
        cli_fn = f"{command.replace('-', '_')}_cli"
        if hasattr(mod, cli_fn):
            return getattr(mod, cli_fn)(sub_argv)
        # fallback: 找第一个 *_cli 函数
        cli_fns = [k for k in dir(mod) if k.endswith("_cli")]
        if cli_fns:
            return getattr(mod, cli_fns[0])(sub_argv)
    print(f"❌ Unknown command: {command}", file=sys.stderr)
    _print_help()
    return 1


def _warn_project_dir_mismatch():
    """v12.18 H3: 串扰机自检（心愿单报告 8.4: 4 台机器 36% 回执缺失集中）。

    OHC_PROJECT_DIR（会话级 env，跨命令残留）与 cwd 推断的项目目录不一致时
    警告——历史教训：持久会话泄漏的 env 指向旧调试目录，污染所有读
    find_project_dir() 的命令（feedback 时间线/回执路径错位）。只警告不阻断
    （合法场景：在 repo 根目录用 env 显式指定远端项目目录）。
    """
    import os
    env_dir = os.environ.get("OHC_PROJECT_DIR", "").strip()
    if not env_dir:
        return
    try:
        from pathlib import Path
        # 独立向上找 SKILL.md（不能走 find_project_dir——它优先返回
        # OHC_PROJECT_DIR 本身，比较会恒等失效）
        d = Path(__file__).resolve().parent.parent
        script_root = None
        for _ in range(5):
            if (d / "SKILL.md").is_file():
                script_root = d
                break
            if d.parent == d:
                break
            d = d.parent
        if script_root is None:
            return
        env_p = Path(env_dir).resolve()
        if env_p != script_root and env_p.exists():
            print(f"⚠️  OHC_PROJECT_DIR={env_p} 与脚本所在项目 {script_root} "
                  f"不一致——若非有意指定（远程项目目录），请清除: "
                  f"unset OHC_PROJECT_DIR",
                  file=sys.stderr)
    except Exception:
        pass


def _print_help():
    print(f"""ohc — OpenHarmony Compile Agent

Usage: python3 ohc-run.py <command> [options]

Commands: {' | '.join(sorted(_MODULES.keys()))}

协作流程 (Git + GitCode PR):
  submit <software> <version>       编译自检，不生成提交单
  review <software> <version>        本地审核辅助，直接扫描目录
  post-merge <software> <version>    PR 合并后重建索引与知识库
  feedback <software> <version>      SKILL_FEEDBACK 流程终态反馈报告

Run 'python3 ohc-run.py <command> --help' for details.""")


if __name__ == "__main__":
    sys.exit(main() or 0)
