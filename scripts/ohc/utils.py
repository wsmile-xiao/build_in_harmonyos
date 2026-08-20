"""Logging and path utilities for ohc."""
import os
import shutil
import sys

# ── Executable finder ──

_COMMON_BIN_DIRS = [
    "/data/service/hnp/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/system/bin",
]


def find_executable(name: str) -> str:
    """Find an executable: env var {NAME}_BIN → PATH → common dirs → fallback."""
    env_key = f"{name.upper()}_BIN"
    env_val = os.environ.get(env_key, "").strip()
    if env_val and os.path.isfile(env_val) and os.access(env_val, os.X_OK):
        return env_val
    found = shutil.which(name)
    if found:
        return found
    for bin_dir in _COMMON_BIN_DIRS:
        candidate = os.path.join(bin_dir, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return name


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
    3. ATOMCODE_HOME environment variable (AtomCode platform)
    4. ~/.atomcode/skills/ (AtomCode platform default path)
    5. ~/.opendesk/ (OpenDesk platform fallback)
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

    # AtomCode platform
    ac_home = os.environ.get("ATOMCODE_HOME", os.path.expanduser("~/.atomcode"))
    for root in [ac_home, os.path.join(os.path.expanduser("~/.atomcode"), "skills")]:
        skill = os.path.join(root, "openharmony-compile-agent", "SKILL.md")
        if os.path.isfile(skill):
            return os.path.dirname(skill)

    # OpenDesk platform fallback
    od_root = os.path.expanduser("~/.opendesk")
    for apps_dir in ["apps/skills/resources", ""]:
        search = os.path.join(od_root, apps_dir, "openharmony-compile-agent", "SKILL.md")
        if os.path.isfile(search):
            return os.path.dirname(search)

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


# ═══════════════════════════════════════════════════════
# Local build cache (v12.6) — 社区安全设计:
#   1. 显式 opt-in: OHC_CCACHE=1 才启用，默认关闭（不污染任何人的环境）
#   2. 隔离: CCACHE_DIR=~/.ohc-ccache + max_size=5G 限额，绝不碰项目目录/CI
#   3. 可复现红线: 一切验证(G0/W3/conan-verify)无条件 CCACHE_DISABLE=1，
#      确保提交的代码在干净 CI 上可复现构建
# ═══════════════════════════════════════════════════════

CCACHE_DIR_DEFAULT = "~/.ohc-ccache"


def ccache_build_env() -> dict:
    """构建期（configure/make 迭代）环境注入。OHC_CCACHE=1 且 ccache 可用时生效。"""
    import shutil
    if os.environ.get("OHC_CCACHE") != "1":
        return {}
    if not shutil.which("ccache"):
        return {}
    d = Path(os.path.expanduser(CCACHE_DIR_DEFAULT))
    d.mkdir(parents=True, exist_ok=True)
    conf = d / "ccache.conf"
    if not conf.exists():
        conf.write_text("max_size = 5G\n", encoding="utf-8")
    env = {"CCACHE_DIR": str(d)}
    # 包装用户已显式指定的编译器（未指定则交给构建系统默认值，不猜）
    for var in ("CC", "CXX"):
        cur = os.environ.get(var, "")
        if cur and not cur.startswith("ccache "):
            env[var] = f"ccache {cur}"
    return env


def ccache_disable_env() -> dict:
    """验证期环境注入：无条件禁用 ccache（社区红线——本地缓存不得影响验证结果）。"""
    return {"CCACHE_DISABLE": "1"}
