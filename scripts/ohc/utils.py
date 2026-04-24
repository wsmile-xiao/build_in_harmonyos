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


def get_agent_id(project_dir: str | None = None) -> str:
    """获取当前协作者的 Agent ID（4位十六进制随机标识）。

    优先级：
    1. 环境变量 OHC_AGENT_ID
    2. 每次调用基于时间戳哈希随机生成（不持久化，避免多协作者冲突）

    Returns:
        4位大写十六进制字符串，如 "A7F3"
    """
    import hashlib
    import time

    # 1. 环境变量
    env_id = os.environ.get("OHC_AGENT_ID", "").strip()
    if env_id:
        return env_id.upper().zfill(4)[:4]

    # 2. 基于时间戳哈希随机生成（每次调用生成新ID，不持久化）
    # 使用当前时间戳的 MD5 哈希前4位，确保每次调用都有不同ID
    ts = str(time.time())
    hash_val = hashlib.md5(ts.encode()).hexdigest()[:4].upper()
    return hash_val
