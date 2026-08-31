"""依赖预编译包解析与安装。

从 cmd-pkgs 仓库动态查询预编译包，自动安装编译所需的依赖软件。

⭐ R18 铁律：预编译包优先，禁止本地缓存。
索引获取方式：每次都从 cmd-pkgs README（远程）获取，不使用本地缓存。

Usage:
    python3 ohc-run.py resolve-deps <software> [<version>]
    python3 ohc-run.py resolve-deps --install <software> [<version>]
    python3 ohc-run.py resolve-deps --list-available
    python3 ohc-run.py resolve-deps --refresh
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail

# ── Constants ──

# cmd-pkgs 仓库的统一通用安装脚本 URL（托管在 pkgs release tag 下）
# 用法: curl -fsSL <url> | sh -s -- <name> <version>
_CMD_PKGS_INSTALL_URL = (
    "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
    "releases/download/pkgs/install.sh"
)

# cmd-pkgs 仓库地址
_CMD_PKGS_REPO = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs.git"

# cmd-pkgs README.md 的 raw URL（通过 git sparse checkout 获取）
_CMD_PKGS_README_RAW = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/raw/main/README.md"


# ═══════════════════════════════════════════════════════
# 预编译包索引（git仓库缓存，每次fetch更新）
# ═══════════════════════════════════════════════════════

# 索引格式: name → {"ver": "x.y.z", "versions": ["x.y.z", ...], "install_script": "install.sh"}
# 多版本软件会在 versions 列表中列出所有可用版本

# 本地git仓库缓存路径（sparse checkout只拉README.md）
_ATOMCODE_CACHE = os.path.expanduser("~/.atomcode/cache/cmd-pkgs")
_OPENDESK_CACHE = os.path.expanduser("~/.opendesk/cache/cmd-pkgs")
_INDEX_CACHE_DIR = _ATOMCODE_CACHE if os.path.isdir(_ATOMCODE_CACHE) else _OPENDESK_CACHE

# 运行时索引
_runtime_index: dict[str, dict] | None = None

# git命令路径（自动检测）
_GIT_CMD: str | None = None

def _find_git() -> str:
    """查找git命令路径。"""
    global _GIT_CMD
    if _GIT_CMD:
        return _GIT_CMD

    # 优先检查常见路径
    candidates = [
        "/data/service/hnp/bin/git",  # OpenHarmony默认位置
        "/usr/bin/git",
        "/usr/local/bin/git",
        os.path.expanduser("~/usr/local/bin/git"),
    ]

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            _GIT_CMD = path
            return path

    # 尝试从PATH查找
    import shutil
    git_path = shutil.which("git")
    if git_path:
        _GIT_CMD = git_path
        return git_path

    raise RuntimeError("git命令未找到，请安装git")


def _run_git(cmd_args: list[str], cwd: str | None = None, **kwargs) -> subprocess.CompletedProcess:
    """执行git命令。"""
    git = _find_git()
    full_cmd = [git] + cmd_args
    return subprocess.run(full_cmd, cwd=cwd, capture_output=True, text=True, timeout=30, **kwargs)


# ═══════════════════════════════════════════════════════
# Core functions
# ═══════════════════════════════════════════════════════

def _get_index() -> dict[str, dict]:
    """获取运行时索引（git仓库缓存，每次fetch更新）。

    流程：
    1. 缓存仓库不存在 → 初始化sparse clone
    2. 缓存仓库存在 → fetch检查更新
    3. 解析README.md并返回索引
    """
    global _runtime_index
    if _runtime_index is not None:
        return _runtime_index

    # 1. 确保缓存仓库存在并更新
    rc = _update_index_repo()
    if rc != 0:
        log_fail("索引仓库更新失败，无法继续。请检查网络连接后重试 --refresh")
        raise RuntimeError("无法获取预编译包索引")

    # 2. 解析README.md
    readme_path = Path(_INDEX_CACHE_DIR) / "README.md"
    if not readme_path.exists():
        log_fail("README.md不存在于缓存仓库")
        raise RuntimeError("缓存仓库缺少README.md")

    content = readme_path.read_text(encoding="utf-8")
    _runtime_index = _parse_readme(content)

    if not _runtime_index:
        log_fail("README解析失败")
        raise RuntimeError("无法解析预编译包索引")

    log_ok(f"索引加载完成: {len(_runtime_index)} 个包")
    return _runtime_index


def _update_index_repo() -> int:
    """更新索引git仓库（初始化或fetch）。

    使用sparse checkout只拉取README.md，减少空间占用。
    每次都fetch检查更新。
    """
    repo_dir = Path(_INDEX_CACHE_DIR)

    # 检查是否是有效的git仓库
    git_dir = repo_dir / ".git"

    if not git_dir.exists():
        # 初始化sparse clone
        log_info("初始化索引仓库（sparse clone）...")
        return _init_sparse_clone()

    # 已存在，fetch检查更新
    log_info("检查索引仓库更新...")
    return _fetch_update()


def _run_git_retry(cmd_args, cwd=None, attempts=3, backoff=(10, 30, 60)):
    """网络类 git 命令重试（反馈 0831 P0-2: 凹晨 registry 不可达多为瞬时抖动，
    单次失败即判 unreachable 造成了 111 例误拒——退避重试后再判）。"""
    result = None
    for i in range(attempts):
        result = _run_git(cmd_args, cwd=cwd)
        if result.returncode == 0:
            return result
        if i < attempts - 1:
            wait = backoff[i] if i < len(backoff) else backoff[-1]
            log_warn(f"git {cmd_args[0]} 失败（第 {i + 1}/{attempts} 次，"
                     f"{result.stderr[:80] if result.stderr else '无输出'}）——{wait}s 后重试")
            time.sleep(wait)
    return result


def _init_sparse_clone() -> int:
    """初始化sparse clone仓库，只拉取README.md。"""
    repo_dir = Path(_INDEX_CACHE_DIR)
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        git = _find_git()
    except RuntimeError as e:
        log_fail(str(e))
        return 1

    # 设置safe.directory避免HMDFS问题
    _run_git(["config", "--global", "--add", "safe.directory", str(repo_dir)])

    cmds = [
        ["init"],
        ["remote", "add", "origin", _CMD_PKGS_REPO],
        ["sparse-checkout", "init", "--cone"],
        ["sparse-checkout", "set", "README.md"],
    ]

    for cmd_args in cmds:
        result = _run_git(cmd_args, cwd=repo_dir)
        if result.returncode != 0:
            log_warn(f"git命令失败: git {' '.join(cmd_args)}")
            return 1

    # fetch 是唯一网络命令——退避重试（反馈 0831 P0-2）
    result = _run_git_retry(["fetch", "--depth=1", "origin", "main"], cwd=repo_dir)
    if result.returncode != 0:
        log_warn(f"git fetch 失败（已重试 3 次）: {result.stderr[:100]}")
        return 1
    _run_git(["checkout", "origin/main"], cwd=repo_dir)

    log_ok("索引仓库初始化完成")
    return 0


def _fetch_update() -> int:
    """fetch检查更新，有更新则checkout。"""
    repo_dir = Path(_INDEX_CACHE_DIR)

    try:
        git = _find_git()
    except RuntimeError as e:
        log_fail(str(e))
        return 1

    # 设置safe.directory
    _run_git(["config", "--global", "--add", "safe.directory", str(repo_dir)])

    # fetch检查更新（网络命令——退避重试，反馈 0831 P0-2）
    result = _run_git_retry(["fetch", "--depth=1", "origin", "main"], cwd=repo_dir)

    if result.returncode != 0:
        log_warn(f"fetch失败（已重试 3 次）: {result.stderr[:100]}")
        return 1

    # 检查是否有更新
    result_local = _run_git(["rev-parse", "HEAD"], cwd=repo_dir)
    result_remote = _run_git(["rev-parse", "origin/main"], cwd=repo_dir)

    local_sha = result_local.stdout.strip()
    remote_sha = result_remote.stdout.strip()

    if local_sha != remote_sha:
        # 有更新，checkout新版本
        log_info("发现新版本，更新索引...")
        result = _run_git(["checkout", "origin/main"], cwd=repo_dir)
        if result.returncode != 0:
            log_warn(f"checkout失败")
            return 1
        log_ok("索引已更新")
    else:
        log_ok("索引无更新")

    return 0


def _parse_readme(content: str) -> dict[str, dict]:
    """解析 README.md 的表格，提取预编译包索引。

    支持的表格格式：
    |软件|版本|安装命令|

    Returns:
        {name: {"ver": "最新版", "versions": [...], "install_script": "install.sh"}}
    """
    index: dict[str, dict] = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("|") or "curl" not in line or "install" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        name = parts[1].strip()
        ver = parts[2].strip()
        cmd = parts[3].strip()
        if not name or not ver or "curl" not in cmd:
            continue

        # 判断安装脚本类型
        if "install-jdk.sh" in cmd:
            install_script = "install-jdk.sh"
        else:
            install_script = "install.sh"

        if name not in index:
            index[name] = {
                "ver": ver,
                "versions": [ver],
                "install_script": install_script,
            }
        else:
            # 多版本：保持第一个遇到的为默认版本，追加到 versions
            if ver not in index[name]["versions"]:
                index[name]["versions"].append(ver)

    return index


# ═══════════════════════════════════════════════════════
# 依赖声明（software-registry.yaml 中的 dependencies）
# ═══════════════════════════════════════════════════════

# 各软件的已知依赖（从实际编译经验总结）
# 格式: software → {"required": [...], "optional": [...]}
# 内置软件索引（软件名 → 默认版本等信息）
# 用于 dispatch 获取版本信息
_BUILTIN_INDEX: dict[str, dict] = {
    "pkg-config":   {"ver": "0.29.2"},
    "pkgconf":      {"ver": "2.2.0"},
    "sed":          {"ver": "4.9"},
    "coreutils":    {"ver": "9.10"},
    "gawk":         {"ver": "5.3.0"},
    "automake":     {"ver": "1.16.5"},
    "autoconf":     {"ver": "2.72"},
    "libtool":      {"ver": "2.4.7"},
    "zlib":         {"ver": "1.3.1"},
    "bzip2":        {"ver": "1.0.8"},
    "xz":           {"ver": "5.6.2"},
    "gzip":         {"ver": "1.13"},
    "openssl":      {"ver": "3.3.1"},
    "ncurses":      {"ver": "6.5"},
    "libffi":       {"ver": "3.4.6"},
    "gdbm":         {"ver": "1.23"},
    "readline":     {"ver": "8.2"},
    "wget":         {"ver": "1.21"},
    "rsync":        {"ver": "3.3.0"},
    "jq":           {"ver": "1.7.1"},
    "tar":          {"ver": "1.35"},
    "file":         {"ver": "5.45"},
    "dos2unix":     {"ver": "7.5.4"},
    "bash":         {"ver": "5.3.0"},
    "htop":         {"ver": "3.3.0"},
    "strace":       {"ver": "6.9"},
    "python":       {"ver": "3.12.9"},
    "man-db":       {"ver": "2.12"},
    "texinfo":      {"ver": "7.1"},
    "help2man":     {"ver": "1.49"},
    "libpipeline":  {"ver": "1.5.7"},
}

_KNOWN_DEPS: dict[str, dict] = {
    "stm32flash":   {"required": [], "optional": []},
    "pkg-config":   {"required": [], "optional": []},
    "sed":          {"required": [], "optional": []},
    "coreutils":    {"required": [], "optional": []},
    "gawk":         {"required": [], "optional": []},
    "automake":     {"required": ["autoconf"], "optional": []},
    "libtool":      {"required": ["automake"], "optional": []},
    "zlib":         {"required": [], "optional": []},
    "bzip2":        {"required": [], "optional": []},
    "xz":           {"required": [], "optional": []},
    "gzip":         {"required": [], "optional": []},
    "openssl":      {"required": ["zlib"], "optional": []},
    "ncurses":      {"required": [], "optional": []},
    "libffi":       {"required": [], "optional": []},
    "gdbm":         {"required": [], "optional": []},
    "readline":     {"required": ["ncurses"], "optional": []},
    "wget":         {"required": ["openssl"], "optional": []},
    "rsync":        {"required": [], "optional": []},
    "jq":           {"required": [], "optional": []},
    "tar":          {"required": [], "optional": []},
    "file":         {"required": [], "optional": []},
    "dos2unix":     {"required": [], "optional": []},
    "bash":         {"required": ["ncurses", "readline"], "optional": []},
    "htop":         {"required": ["ncurses"], "optional": []},
    "strace":       {"required": [], "optional": []},
    "python":       {"required": ["openssl", "zlib", "libffi", "ncurses", "readline", "gdbm", "xz", "bzip2"], "optional": []},
    "man-db":       {"required": ["gdbm", "libpipeline"], "optional": []},
    "texinfo":      {"required": [], "optional": []},
    "help2man":     {"required": [], "optional": []},
    "libpipeline":  {"required": [], "optional": []},
}

# 内建版本索引（作为最后回退）
# 格式: software → {"ver": "x.y.z"}
_BUILTIN_INDEX: dict[str, dict] = {
    "podman":       {"ver": "5.8.3"},
    "libseccomp":   {"ver": "2.6.0"},
    "xterm":        {"ver": "410"},
    "xclip":        {"ver": "0.13"},
}


# ═══════════════════════════════════════════════════════
# 内置软件版本索引（后备）
# ═══════════════════════════════════════════════════════

# 格式: software → {"ver": "x.y.z", "url": "...", "build_system": "autotools|cmake|make"}
_BUILTIN_INDEX: dict[str, dict] = {
    "stm32flash":   {"ver": "0.7", "url": "https://sourceforge.net/projects/stm32flash/files/stm32flash-0.7.tar.gz", "build_system": "make"},
}


# ═══════════════════════════════════════════════════════
# 通用工具检查与自动安装（泛化 R18 扩展）
# ═══════════════════════════════════════════════════════

# 工具名 → cmd-pkgs 包名映射（动态扩展）
# 有些工具名和包名不同，需要映射
_TOOL_TO_PACKAGE_MAP = {
    # 工具名: (cmd_pkgs包名, 默认版本)
    "sed": ("sed", "4.9"),
    "gawk": ("gawk", "5.3.0"),
    "awk": ("gawk", "5.3.0"),  # awk 通常指向 gawk
    "grep": ("grep", "3.11"),  # grep 可能不在 cmd-pkgs，查实际可用
    "find": ("findutils", "4.9"),  # find 属于 findutils
    "install": ("coreutils", "9.10"),  # install 属于 coreutils
    "cp": ("coreutils", "9.10"),
    "mv": ("coreutils", "9.10"),
    "ls": ("coreutils", "9.10"),
    "cat": ("coreutils", "9.10"),
    "head": ("coreutils", "9.10"),
    "tail": ("coreutils", "9.10"),
    "cut": ("coreutils", "9.10"),
    "sort": ("coreutils", "9.10"),
    "uniq": ("coreutils", "9.10"),
    "tr": ("coreutils", "9.10"),
    "automake": ("automake", "1.16.5"),
    "autoconf": ("autoconf", "2.72"),  # 可能不在 cmd-pkgs
    "libtool": ("libtool", "2.4.7"),
    "pkg-config": ("pkg-config", "0.29.2"),
    "make": ("make", "4.4"),  # GNU make
    "cmake": ("cmake", "3.28"),  # 可能不在 cmd-pkgs
    "ninja": ("ninja", "1.11"),  # 可能不在 cmd-pkgs
    "meson": ("meson", "1.3"),  # 可能不在 cmd-pkgs
    "python": ("python", "3.12.9"),
    "python3": ("python", "3.12.9"),
    "perl": ("perl", "5.38"),  # 可能不在 cmd-pkgs
    "curl": ("curl", "8.6"),  # curl 可能在 cmd-pkgs
    "wget": ("wget", "1.21"),
    "tar": ("tar", "1.35"),
    "gzip": ("gzip", "1.13"),
    "bzip2": ("bzip2", "1.0.8"),
    "xz": ("xz", "5.6.2"),
    "unzip": ("unzip", "6.0"),  # 可能不在 cmd-pkgs
    "patch": ("patch", "2.7"),  # 可能不在 cmd-pkgs
    "diff": ("diffutils", "3.10"),  # 可能不在 cmd-pkgs
    "file": ("file", "5.45"),
    "jq": ("jq", "1.7.1"),
    "rsync": ("rsync", "3.3.0"),
    "dos2unix": ("dos2unix", "7.5.4"),
    "help2man": ("help2man", "1.49"),  # 可能不在 cmd-pkgs
    "texinfo": ("texinfo", "7.1"),  # 可能不在 cmd-pkgs
}


def check_tool_available(tool_name: str, prefix: str | None = None) -> tuple[bool, str]:
    """检查工具是否可用，返回 (是否可用, 版本或原因)。

    Args:
        tool_name: 工具名（如 sed, gawk, automake）
        prefix: 安装前缀（默认 ~/usr/local）

    Returns:
        (True, "GNU sed 4.9") 或 (False, "未安装") 或 (False, "toybox 版本")
    """
    import shutil

    prefix = prefix or os.path.expanduser("~/usr/local")

    # 优先检查 ~/usr/local/bin（我们安装的 GNU 版本）
    local_bin = os.path.join(prefix, "bin", tool_name)
    if os.path.isfile(local_bin) and os.access(local_bin, os.X_OK):
        # 尝试获取版本
        try:
            result = subprocess.run(
                [local_bin, "--version"],
                capture_output=True, text=True, timeout=5
            )
            first_line = result.stdout.split("\n")[0] if result.stdout else ""
            if result.returncode == 0 and first_line:
                return True, first_line[:50]
        except:
            pass
        return True, f"{local_bin}"

    # 检查系统 PATH
    tool_path = shutil.which(tool_name)
    if not tool_path:
        return False, "未安装"

    # 获取版本信息
    try:
        result = subprocess.run(
            [tool_path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        first_line = result.stdout.split("\n")[0] if result.stdout else ""

        if result.returncode == 0 and "GNU" in first_line:
            return True, first_line[:50]
        elif result.returncode == 0 and first_line:
            # 非 GNU 但有版本输出
            return True, f"非GNU: {first_line[:30]}"
        else:
            # 可能是 toybox（不支持 --version）
            # 尝试其他方式判断
            try:
                result2 = subprocess.run(
                    [tool_path, "--help"],
                    capture_output=True, text=True, timeout=3
                )
                if "toybox" in result2.stdout.lower() or "toybox" in result2.stderr.lower():
                    return False, "toybox 版本（功能受限）"
            except:
                pass
            return True, f"系统版本 ({tool_path})"
    except subprocess.TimeoutExpired:
        return True, f"系统版本 ({tool_path})"
    except Exception:
        return True, f"系统版本 ({tool_path})"


def get_package_for_tool(tool_name: str) -> tuple[str | None, str | None]:
    """根据工具名获取对应的 cmd-pkgs 包名和版本。

    Args:
        tool_name: 工具名

    Returns:
        (包名, 版本) 或 (None, None) 如果无映射
    """
    # 先查映射表
    if tool_name in _TOOL_TO_PACKAGE_MAP:
        pkg_name, pkg_ver = _TOOL_TO_PACKAGE_MAP[tool_name]
        # 验证 cmd-pkgs 是否真的有这个包
        if is_prebuilt_available(pkg_name):
            actual_ver = get_available_version(pkg_name) or pkg_ver
            return pkg_name, actual_ver
        # 映射表中有但 cmd-pkgs 无，返回 None
        return None, None

    # 工具名直接作为包名尝试（很多情况下一致）
    if is_prebuilt_available(tool_name):
        return tool_name, get_available_version(tool_name)

    return None, None


def auto_install_tool(tool_name: str, prefix: str | None = None) -> int:
    """自动检查并安装缺失的工具。

    Args:
        tool_name: 工具名
        prefix: 安装前缀

    Returns:
        0=已安装或安装成功, 1=无预编译包或安装失败
    """
    available, info = check_tool_available(tool_name, prefix)
    if available:
        log_ok(f"工具 {tool_name} 已可用: {info}")
        return 0

    # 尝试从 cmd-pkgs 安装
    pkg_name, pkg_ver = get_package_for_tool(tool_name)
    if not pkg_name:
        log_warn(f"工具 {tool_name} 无预编译包，需手动安装")
        return 1

    log_info(f"安装工具 {tool_name}（包: {pkg_name} {pkg_ver})")
    return install_prebuilt(pkg_name, pkg_ver, prefix)


def auto_install_missing_tools_from_log(log_text: str, prefix: str | None = None) -> list[str]:
    """分析错误日志，自动安装缺失的工具。

    从日志中提取 "command not found"、"which: no xxx" 等模式，
    自动识别缺失的工具并安装。

    Args:
        log_text: 错误日志文本
        prefix: 安装前缀

    Returns:
        安装成功的工具列表
    """
    import re

    patterns = [
        r"([a-zA-Z0-9_-]+): command not found",
        r"which: no ([a-zA-Z0-9_-]+) in",
        r"([a-zA-Z0-9_-]+): not found",
        r"checking for ([a-zA-Z0-9_-]+)\.\.\. no",
        r"configure: error: ([a-zA-Z0-9_-]+) not found",
        r"Can't locate ([a-zA-Z0-9_-]+)",  # Perl 模块
    ]

    missing_tools = set()
    for pattern in patterns:
        matches = re.findall(pattern, log_text, re.IGNORECASE)
        for m in matches:
            tool_name = m.lower()
            # 过滤掉一些非工具的匹配（如库文件名）
            if tool_name.endswith(".so") or tool_name.endswith(".a"):
                continue
            if tool_name.startswith("lib"):
                continue
            missing_tools.add(tool_name)

    installed = []
    for tool in sorted(missing_tools):
        pkg_name, pkg_ver = get_package_for_tool(tool)
        if pkg_name:
            log_info(f"发现缺失工具: {tool} → 自动安装 {pkg_name} {pkg_ver}")
            rc = install_prebuilt(pkg_name, pkg_ver, prefix)
            if rc == 0:
                installed.append(tool)
            else:
                log_warn(f"  安装失败: {tool}")
        else:
            log_warn(f"发现缺失工具: {tool} → 无预编译包")

    return installed


def check_common_build_tools(prefix: str | None = None) -> dict[str, tuple[bool, str]]:
    """检查常见构建工具的可用性，返回状态字典。

    Args:
        prefix: 安装前缀

    Returns:
        {tool_name: (is_available, version_info)}
    """
    common_tools = [
        "sed", "gawk", "grep", "find", "make",
        "automake", "autoconf", "libtool", "pkg-config",
        "curl", "tar", "gzip", "bzip2", "xz",
        "patch", "file", "diff",
    ]

    results = {}
    for tool in common_tools:
        results[tool] = check_tool_available(tool, prefix)

    return results


# ═══════════════════════════════════════════════════════
# Public API: 预编译包检查
# ═══════════════════════════════════════════════════════

def get_install_url(name: str) -> str | None:
    """获取预编译包的安装命令 URL。"""
    idx = _get_index()
    info = idx.get(name)
    if not info:
        return None
    script = info.get("install_script", "install.sh")
    base = _CMD_PKGS_INSTALL_URL.rsplit("/", 1)[0]
    return f"{base}/{script}"


def get_available_version(name: str) -> str | None:
    """获取预编译包的默认版本。"""
    idx = _get_index()
    info = idx.get(name)
    if not info:
        return None
    return info.get("ver")


def get_available_versions(name: str) -> list[str]:
    """获取预编译包的所有可用版本。"""
    idx = _get_index()
    info = idx.get(name)
    if not info:
        return []
    return info.get("versions", [info.get("ver", "")])


def is_prebuilt_available(name: str) -> bool:
    """检查是否有预编译包可用。"""
    return name in _get_index()


def is_installed(name: str, prefix: str | None = None) -> bool:
    """检查软件是否已安装到目标 prefix。

    通过检查 $PREFIX/bin/{name} 或 $PREFIX/lib/lib{name}.so 是否存在判断。
    """
    p = prefix or os.path.expanduser("~/usr/local")
    bin_path = os.path.join(p, "bin", name)
    if os.path.isfile(bin_path) and os.access(bin_path, os.X_OK):
        return True
    # Some packages install with different binary names
    _ALTERNATE_BINARIES = {
        "pkg-config": ["pkg-config"],
        "coreutils": ["ls", "cat", "cp"],  # coreutils installs many commands
        "libffi": [],  # no binary, only library
        "zlib": [],    # no binary, only library
        "ncurses": [],  # installs lib, not always bin
        "readline": [],  # library only
    }
    alts = _ALTERNATE_BINARIES.get(name, [name])
    for alt in alts:
        bp = os.path.join(p, "bin", alt)
        if os.path.isfile(bp) and os.access(bp, os.X_OK):
            return True
    # Check library for library-only packages
    _LIB_PACKAGES = {"libffi", "zlib", "ncurses", "readline", "gdbm", "openssl"}
    if name in _LIB_PACKAGES:
        lib_dir = os.path.join(p, "lib")
        if os.path.isdir(lib_dir):
            for f in os.listdir(lib_dir):
                if name.replace("-", "") in f.replace("-", "").replace(".", "").lower():
                    return True
                # Check for .a static libs
                fn = f.lower().replace("-", "").replace(".", "")
                if name.replace("-", "").replace(".", "") in fn:
                    return True
    # Check pkg-config
    pc_dir = os.path.join(p, "lib", "pkgconfig")
    if os.path.isdir(pc_dir):
        for f in os.listdir(pc_dir):
            if name.replace("-", "").lower() in f.replace("-", "").lower():
                return True
    return False


def get_missing_deps(software: str, prefix: str | None = None) -> list[str]:
    """获取编译某软件所需的、尚未安装的依赖列表。

    Args:
        software: 软件名称
        prefix: 安装前缀（默认 ~/usr/local）

    Returns:
        未安装的依赖名称列表（按安装顺序）。
    """
    deps_info = _KNOWN_DEPS.get(software, {})
    required = deps_info.get("required", [])
    missing = []
    for dep in required:
        if not is_installed(dep, prefix):
            if is_prebuilt_available(dep):
                missing.append(dep)
            else:
                missing.append(dep)  # 仍然列出，即使没有预编译包
    return missing


def install_prebuilt(name: str, version: str = "", prefix: str | None = None) -> int:
    """通过 curl | sh 安装预编译包。"""
    # Security: validate name and version to prevent command injection
    _SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    if not name or not _SAFE_PATTERN.match(name):
        log_fail(f"无效的包名(含非法字符): {name!r}")
        return 1
    if version and not _SAFE_PATTERN.match(version):
        log_fail(f"无效的版本号(含非法字符): {version!r}")
        return 1

    idx = _get_index()
    info = idx.get(name)
    if not info:
        log_fail(f"无预编译包: {name}")
        return 1

    install_url = get_install_url(name)
    if not install_url:
        log_fail(f"无法获取安装 URL: {name}")
        return 1

    if not version:
        version = info.get("ver", "")

    log_info(f"安装预编译包: {name} {version}")
    log_info(f"  来源: {install_url}")

    install_prefix = prefix or os.path.expanduser("~/usr/local")
    # Security: use shlex.quote to escape name and version (defense-in-depth)
    cmd = f'curl -fsSL "{install_url}" | sh -s -- {shlex.quote(name)} {shlex.quote(version)}'

    log_info(f"  执行: {cmd}")

    env = os.environ.copy()
    env.setdefault("PREFIX", install_prefix)

    try:
        result = subprocess.run(
            ["sh", "-c", cmd],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            log_ok(f"  安装成功: {name} {version}")
            return 0
        else:
            log_fail(f"  安装失败 (exit {result.returncode})")
            if result.stderr:
                err_lines = result.stderr.strip().split("\n")[-5:]
                for line in err_lines:
                    print(f"    {line}", file=sys.stderr)
            return 1
    except subprocess.TimeoutExpired:
        log_fail(f"  安装超时 (300s)")
        return 1
    except Exception as e:
        log_fail(f"  安装异常: {e}")
        return 1


def resolve_and_install(software: str, version: str = "",
                        prefix: str | None = None,
                        dry_run: bool = False) -> int:
    """解析依赖并安装缺失的预编译包。

    Args:
        software: 目标软件名
        version: 目标版本
        prefix: 安装前缀
        dry_run: 仅显示需要安装的依赖，不实际安装

    Returns:
        0=全部就绪, 1=有依赖无法满足
    """
    prefix = prefix or os.path.expanduser("~/usr/local")

    missing = get_missing_deps(software, prefix)

    if not missing:
        log_ok(f"所有依赖已就绪: {software}")
        return 0

    log_info(f"发现 {len(missing)} 个缺失依赖: {', '.join(missing)}")

    unavailable = [d for d in missing if not is_prebuilt_available(d)]
    if unavailable:
        log_warn(f"  无预编译包（需自行编译）: {', '.join(unavailable)}")

    installable = [d for d in missing if is_prebuilt_available(d)]
    if not installable:
        if unavailable:
            log_fail(f"所有缺失依赖都没有预编译包，请先手动编译: {', '.join(unavailable)}")
        return 1

    if dry_run:
        for dep in installable:
            ver = get_available_version(dep)
            url = get_install_url(dep)
            print(f"  可安装: {dep} {ver}")
            print(f"    命令: curl -fsSL {url} | sh -s -- {ver}")
        for dep in unavailable:
            print(f"  需编译: {dep}（无预编译包）")
        return 0

    # Actually install
    failed = []
    for dep in installable:
        ver = get_available_version(dep)
        rc = install_prebuilt(dep, ver, prefix)
        if rc != 0:
            failed.append(dep)

    if failed:
        log_fail(f"以下依赖安装失败: {', '.join(failed)}")
        return 1

    log_ok(f"依赖安装完成: {', '.join(installable)}")
    return 0


def list_available() -> None:
    """列出所有可用的预编译包。"""
    idx = _get_index()
    print(f"\n  📦 可用预编译包 ({len(idx)} 个):\n")
    print(f"  {'软件':<15} {'版本':<12} {'已安装':<8} {'安装命令'}")
    print(f"  {'─' * 80}")

    prefix = os.path.expanduser("~/usr/local")

    for name in sorted(idx.keys()):
        info = idx[name]
        ver = info.get("ver", "?")
        versions = info.get("versions", [])
        installed = "✅" if is_installed(name, prefix) else "❌"
        url = get_install_url(name)
        ver_display = ver if len(versions) <= 1 else f"{ver} (+{len(versions)-1})"
        print(f"  {name:<15} {ver_display:<12} {installed:<8} curl -fsSL {url} | sh -s -- {name} {ver}")
        if len(versions) > 1:
            for v in versions:
                if v != ver:
                    print(f"  {'':15} {v:<12} {'':8} curl -fsSL {url} | sh -s -- {name} {v}")
    print()


# ═══════════════════════════════════════════════════════
# Refresh index
# ═══════════════════════════════════════════════════════

def refresh_index(pdir: str | None = None) -> int:
    """强制刷新索引仓库（重新clone）。"""
    global _runtime_index

    # 清除运行时缓存
    _runtime_index = None

    # 删除旧仓库并重新clone
    repo_dir = Path(_INDEX_CACHE_DIR)
    if repo_dir.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)
        log_info("删除旧缓存仓库...")

    log_info("强制重新clone索引仓库...")
    return _init_sparse_clone()


# ═══════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════

def _topo_layers_packages(pkgs: list[str], prefix: str | None = None) -> list[list[str]]:
    """包级拓扑分层：同层互不依赖可并行（v12.6 L3b，社区多机/多进程排程）。

    每包的缺失依赖来自 get_missing_deps；若某依赖也在包集合内，则该包须排后层。
    """
    dep_map = {p: [d for d in get_missing_deps(p, prefix) if d in pkgs] for p in pkgs}
    resolved: set[str] = set()
    layers, pending = [], list(pkgs)
    while pending:
        layer = [p for p in pending if not [d for d in dep_map[p] if d not in resolved]]
        if not layer:
            layers.append(pending)  # 依赖环兜底
            break
        layers.append(layer)
        resolved.update(layer)
        pending = [p for p in pending if p not in layer]
    return layers


def resolve_deps_cli(argv: list[str] | None = None) -> int:
    """CLI entry point: ohc resolve-deps"""
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc resolve-deps",
        description="查询并安装编译依赖的预编译包",
    )
    parser.add_argument("software", nargs="?", help="目标软件名")
    parser.add_argument("version", nargs="?", default="", help="版本号")
    parser.add_argument("--install", "-i", action="store_true",
                        help="自动安装缺失的依赖")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="仅显示需要安装的依赖，不实际安装")
    parser.add_argument("--list-available", "-l", action="store_true",
                        help="列出所有可用的预编译包")
    parser.add_argument("--refresh", action="store_true",
                        help="从远程仓库刷新索引")
    parser.add_argument("--check-tools", "-t", action="store_true",
                        help="检查常见构建工具可用性")
    parser.add_argument("--batch", "-b", metavar="FILE",
                        help="批量模式：文件内每行一个包名，输出拓扑分层（同层可并行）")
    parser.add_argument("--prefix", default=None,
                        help="安装前缀（默认 ~/usr/local）")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)

    if args.batch:
        from pathlib import Path as _P
        lines = [ln.strip() for ln in _P(args.batch).read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
        layers = _topo_layers_packages(lines, args.prefix)
        print("📦 拓扑分层（同层可并行，层间按序）:")
        for i, layer in enumerate(layers):
            print(f"  Layer {i}: {' | '.join(layer)}")
        print(f"\n  并行提示: 每层包可在不同 workdir/机器并发执行 ohc build（状态文件已加锁，v12.6）")
        return 0

    if args.refresh:
        return refresh_index(getattr(args, "project_dir", None))

    if args.list_available:
        list_available()
        return 0

    if args.check_tools:
        # ⭐ 新增：检查常见构建工具
        print("\n  🔧 构建工具可用性检查:\n")
        print(f"  {'工具':<12} {'状态':<8} {'版本信息'}")
        print(f"  {'─' * 60}")

        results = check_common_build_tools(args.prefix)
        for tool, (available, info) in results.items():
            status = "✅" if available else "❌"
            pkg_name, pkg_ver = get_package_for_tool(tool)
            pkg_hint = f"（可安装: {pkg_name} {pkg_ver})" if pkg_name and not available else ""
            print(f"  {tool:<12} {status:<8} {info[:40]}{pkg_hint}")

        # 统计缺失工具
        missing = [t for t, (a, _) in results.items() if not a]
        if missing:
            print(f"\n  ⚠️ 缺失工具: {', '.join(missing)}")
            print(f"  安装命令:")
            for tool in missing:
                pkg_name, pkg_ver = get_package_for_tool(tool)
                if pkg_name:
                    print(f"    curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- {pkg_name} {pkg_ver}")
        else:
            print(f"\n  ✅ 所有构建工具已就绪")
        print()
        return 0

    if not args.software:
        log_fail("请指定软件名，或使用 --list-available / --refresh / --check-tools")
        return 1

    return resolve_and_install(
        args.software, args.version,
        prefix=args.prefix,
        dry_run=args.dry_run or not args.install,
    )
