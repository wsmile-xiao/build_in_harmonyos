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
    2. 项目根目录下的 .agent-id 文件
    3. 自动生成并持久化到 .agent-id 文件

    Returns:
        4位大写十六进制字符串，如 "A7F3"
    """
    import random

    # 1. 环境变量
    env_id = os.environ.get("OHC_AGENT_ID", "").strip()
    if env_id:
        return env_id.upper().zfill(4)[:4]

    # 2. 项目根目录下的 .agent-id 文件
    pdir = project_dir or find_project_dir()
    agent_id_file = os.path.join(pdir, ".agent-id")
    if os.path.isfile(agent_id_file):
        try:
            existing = open(agent_id_file, "r", encoding="utf-8").read().strip()
            if existing:
                return existing.upper().zfill(4)[:4]
        except OSError:
            pass

    # 3. 自动生成并持久化
    new_id = f"{random.randint(0, 0xFFFF):04X}"
    try:
        with open(agent_id_file, "w", encoding="utf-8") as f:
            f.write(new_id + "\n")
    except OSError:
        pass  # 如果无法写入文件，仅使用内存中的 ID

    return new_id
