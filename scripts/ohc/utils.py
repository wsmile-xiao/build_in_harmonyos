"""Logging and path utilities for ohc."""
import os
import sys

# ── ANSI colors ──
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _supports_color() -> bool:
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def log_info(msg: str) -> None:
    prefix = f"{_CYAN}ℹ️{_RESET} " if _supports_color() else "ℹ️ "
    print(f"  {prefix}{msg}", file=sys.stderr)


def log_ok(msg: str) -> None:
    prefix = f"{_GREEN}✅{_RESET} " if _supports_color() else "✅ "
    print(f"  {prefix}{msg}", file=sys.stderr)


def log_warn(msg: str) -> None:
    prefix = f"{_YELLOW}⚠️{_RESET} " if _supports_color() else "⚠️ "
    print(f"  {prefix}{msg}", file=sys.stderr)


def log_fail(msg: str) -> None:
    prefix = f"{_RED}❌{_RESET} " if _supports_color() else "❌ "
    print(f"  {prefix}{msg}", file=sys.stderr)


def find_project_dir() -> str:
    """Locate the openharmony-compile-agent root directory.

    Search order:
    1. OHC_PROJECT_DIR environment variable
    2. Walk upward from this script's location to find SKILL.md
    """
    env = os.environ.get("OHC_PROJECT_DIR")
    if env and os.path.isfile(os.path.join(env, "SKILL.md")):
        return env

    # Walk up from scripts/ohc/
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _ in range(5):
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent

    # Fallback: cwd
    return os.getcwd()


def graph_dir(project_dir: str | None = None) -> str:
    """Return knowledge/graph/ directory path."""
    return os.path.join(project_dir or find_project_dir(), "knowledge", "graph")
