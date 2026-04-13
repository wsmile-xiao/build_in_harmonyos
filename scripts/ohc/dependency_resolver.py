"""依赖预编译包解析与安装。

从 cmd-pkgs 仓库查询预编译包，自动安装编译所需的依赖软件。

Usage:
    python3 ohc-run.py resolve-deps <software> [<version>]
    python3 ohc-run.py resolve-deps --install <software> [<version>]
    python3 ohc-run.py resolve-deps --list-available
"""
from __future__ import annotations

import os
import re
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail

# ── Constants ──

# cmd-pkgs 仓库的预编译包安装 URL 模板
_CMD_PKGS_INSTALL_URL = (
    "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
    "releases/download/{name}/install.sh"
)

# Python 有独立的安装源
_PYTHON_INSTALL_URL = (
    "https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release/"
    "releases/download/installer/install.sh"
)

# README 索引缓存路径（项目根目录下）
_CACHE_FILE = ".cmd-pkgs-cache.tsv"

# HarmonyOS 环境可能缺少 CA 证书
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ═══════════════════════════════════════════════════════
# 预编译包索引（内置 + 可刷新）
# ═══════════════════════════════════════════════════════

# 内置索引：从 cmd-pkgs README.md 提取的已知预编译包
# 格式: name → (version, install_url_template)
# special="python" 表示使用 python 专用安装源
_BUILTIN_INDEX: dict[str, dict] = {
    "pkg-config":  {"ver": "0.29.2", "source": "cmd-pkgs"},
    "python":      {"ver": "3.12.9", "source": "python", "versions": ["3.9.0", "3.9.25", "3.12.9"]},
    "sed":         {"ver": "4.9",    "source": "cmd-pkgs"},
    "coreutils":   {"ver": "9.10",   "source": "cmd-pkgs"},
    "gawk":        {"ver": "5.3.0",  "source": "cmd-pkgs"},
    "automake":    {"ver": "1.16.5", "source": "cmd-pkgs"},
    "libtool":     {"ver": "2.4.7",  "source": "cmd-pkgs"},
    "zlib":        {"ver": "1.3.1",  "source": "cmd-pkgs"},
    "bzip2":       {"ver": "1.0.8",  "source": "cmd-pkgs"},
    "xz":          {"ver": "5.6.2",  "source": "cmd-pkgs"},
    "gzip":        {"ver": "1.13",   "source": "cmd-pkgs"},
    "openssl":     {"ver": "1.1.1w", "source": "cmd-pkgs"},
    "libffi":      {"ver": "3.5.2",  "source": "cmd-pkgs"},
    "ncurses":     {"ver": "6.4",    "source": "cmd-pkgs"},
    "gdbm":        {"ver": "1.23",   "source": "cmd-pkgs"},
    "readline":    {"ver": "8.2",    "source": "cmd-pkgs"},
    "wget":        {"ver": "1.19.1", "source": "cmd-pkgs"},
    "rsync":       {"ver": "3.3.0",  "source": "cmd-pkgs"},
    "jq":          {"ver": "1.7.1",  "source": "cmd-pkgs"},
    "tar":         {"ver": "1.35",   "source": "cmd-pkgs"},
    "file":        {"ver": "5.45",   "source": "cmd-pkgs"},
    "dos2unix":    {"ver": "7.5.4",  "source": "cmd-pkgs"},
}


# ═══════════════════════════════════════════════════════
# 依赖声明（software-registry.yaml 中的 dependencies）
# ═══════════════════════════════════════════════════════

# 各软件的已知依赖（从实际编译经验总结）
# 格式: software → {"required": [...], "optional": [...]}
_KNOWN_DEPS: dict[str, dict] = {
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


# ═══════════════════════════════════════════════════════
# Core functions
# ═══════════════════════════════════════════════════════

def get_install_url(name: str) -> str | None:
    """获取预编译包的安装命令 URL。

    Returns:
        install.sh 的 URL，或 None（如果没有预编译包）。
    """
    info = _BUILTIN_INDEX.get(name)
    if not info:
        return None

    source = info.get("source", "cmd-pkgs")
    if source == "python":
        return _PYTHON_INSTALL_URL
    else:
        return _CMD_PKGS_INSTALL_URL.format(name=name)


def get_available_version(name: str) -> str | None:
    """获取预编译包的可用版本。"""
    info = _BUILTIN_INDEX.get(name)
    if not info:
        return None
    return info.get("ver")


def is_prebuilt_available(name: str) -> bool:
    """检查是否有预编译包可用。"""
    return name in _BUILTIN_INDEX


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
    """通过 curl | sh 安装预编译包。

    Args:
        name: 软件名称
        version: 版本号（空则使用默认版本）
        prefix: 安装路径

    Returns:
        0=成功, 1=失败
    """
    info = _BUILTIN_INDEX.get(name)
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

    # Build command
    install_prefix = prefix or os.path.expanduser("~/usr/local")
    cmd = f'curl -fsSL "{install_url}" | sh -s -- {version}'

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
                # Print last 5 lines of error
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
    print(f"\n  📦 可用预编译包 ({len(_BUILTIN_INDEX)} 个):\n")
    print(f"  {'软件':<15} {'版本':<12} {'已安装':<8} {'安装命令'}")
    print(f"  {'─' * 80}")

    prefix = os.path.expanduser("~/usr/local")

    for name in sorted(_BUILTIN_INDEX.keys()):
        info = _BUILTIN_INDEX[name]
        ver = info.get("ver", "?")
        installed = "✅" if is_installed(name, prefix) else "❌"
        url = get_install_url(name)
        print(f"  {name:<15} {ver:<12} {installed:<8} curl -fsSL {url} | sh -s -- {ver}")
    print()


# ═══════════════════════════════════════════════════════
# Refresh index from remote README
# ═══════════════════════════════════════════════════════

def refresh_index(pdir: str | None = None) -> int:
    """从 cmd-pkgs 仓库刷新预编译包索引。"""
    project_dir = Path(pdir or find_project_dir())

    log_info("从 cmd-pkgs 仓库刷新预编译包索引...")

    readme_url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/-/raw/main/README.md"
    try:
        req = urllib.request.Request(readme_url, headers={"User-Agent": "ohc/1.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=30)
        except urllib.error.URLError:
            resp = urllib.request.urlopen(req, timeout=30, context=_SSL_CTX)
        content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log_warn(f"无法获取远程索引: {e}")
        log_info("使用内置索引")
        return 0

    # Parse README table: |软件|版本|安装命令|
    count = 0
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("|") and "curl" in line and "install.sh" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                name = parts[1].strip()
                ver = parts[2].strip()
                cmd = parts[3].strip()
                if name and ver and "curl" in cmd:
                    # Determine source
                    if "ohos-python-release" in cmd:
                        source = "python"
                    else:
                        source = "cmd-pkgs"
                    _BUILTIN_INDEX[name] = {"ver": ver, "source": source}
                    count += 1

    if count:
        log_ok(f"刷新完成: {count} 个预编译包")

    # Save cache
    cache_path = project_dir / _CACHE_FILE
    lines = ["name\tversion\tsource"]
    for name in sorted(_BUILTIN_INDEX.keys()):
        info = _BUILTIN_INDEX[name]
        lines.append(f"{name}\t{info.get('ver', '')}\t{info.get('source', 'cmd-pkgs')}")
    cache_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


# ═══════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════

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
    parser.add_argument("--prefix", default=None,
                        help="安装前缀（默认 ~/usr/local）")
    parser.add_argument("--project-dir", "-p", default=None)
    args = parser.parse_args(argv)

    if args.refresh:
        return refresh_index(getattr(args, "project_dir", None))

    if args.list_available:
        list_available()
        return 0

    if not args.software:
        log_fail("请指定软件名，或使用 --list-available / --refresh")
        return 1

    return resolve_and_install(
        args.software, args.version,
        prefix=args.prefix,
        dry_run=args.dry_run or not args.install,
    )
