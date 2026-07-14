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
}


def main() -> int:
    if len(sys.argv) < 2:
        _print_help()
        return 0
    command = sys.argv[1]
    sub_argv = sys.argv[2:]
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
