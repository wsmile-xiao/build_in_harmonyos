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
    "verify-build": "verify_build", "sign-elf": "sign_elf",
    "package": "package_builder",
    "summary": "summary",
    "submit": "submission",
    "review": "submission",
    "approve": "submission",
    "reject": "submission",
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

Run 'python3 ohc-run.py <command> --help' for details.""")


if __name__ == "__main__":
    sys.exit(main() or 0)
