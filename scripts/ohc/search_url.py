"""Search download URL for software packages.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn


def _head(url: str, timeout: int = 5) -> int:
    """HTTP HEAD request, return status code or 0 on failure."""
    try:
        r = subprocess.run(
            ["curl", "-sI", "--connect-timeout", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 2,
        )
        first_line = (r.stdout or "").split("\n")[0]
        # Parse "HTTP/2 200" or "HTTP/1.1 302"
        parts = first_line.split()
        if len(parts) >= 2:
            return int(parts[1])
        return 0
    except Exception:
        return 0


def search_url(name: str, version: str = "latest", pdir: str | None = None) -> int:
    log_info(f"搜索下载 URL: {name} {version}")
    found: list[str] = []

    # Strategy 1: GNU FTP
    for ext in ["tar.gz", "tar.xz", "tar.bz2"]:
        url = f"https://ftp.gnu.org/gnu/{name}/{name}-{version}.{ext}"
        code = _head(url)
        if code in (200, 302):
            log_ok(f"  ✅ [GNU FTP] {url}")
            found.append(url)

    # Strategy 2: GitHub Releases
    for org in [name, f"gnu-{name}", f"{name}-project", f"lib{name}"]:
        url = f"https://github.com/{org}/{name}/releases/download/v{version}/{name}-{version}.tar.gz"
        code = _head(url)
        if code in (200, 302):
            log_ok(f"  ✅ [GitHub] {url}")
            found.append(url)

    # Strategy 3: freedesktop / Savannah
    for base in [f"{name}.freedesktop.org/releases",
                 f"{name}.io/files",
                 f"download.savannah.nongnu.org/releases/{name}"]:
        for ext in ["tar.gz", "tar.xz"]:
            url = f"https://{base}/{name}-{version}.{ext}"
            code = _head(url)
            if code in (200, 302):
                log_ok(f"  ✅ [freedesktop/Savannah] {url}")
                found.append(url)

    # Strategy 4: Official sites
    for base in [f"www.{name}.org", f"{name}.org",
                 f"tukaani.org/{name}", "www.zlib.net",
                 f"astron.com/pub/{name}", f"waterlan.home.xs4all.nl/{name}"]:
        for ext in ["tar.gz", "tar.xz"]:
            url = f"https://{base}/{name}-{version}.{ext}"
            code = _head(url)
            if code in (200, 302):
                log_ok(f"  ✅ [Official] {url}")
                found.append(url)

    # Strategy 5: Search engine hint
    print(f"\n  💡 搜索引擎: https://duckduckgo.com/?q={name}+{version}+download+tar.gz")

    if found:
        print(f"\n  📋 找到 {len(found)} 个可用 URL:")
        for u in found:
            print(f"    {u}")
        print(f"\n  用法: python3 ohc-run.py init {name} {version} --url={found[0]}")
    else:
        log_warn(f"未找到 {name} {version} 的自动下载 URL")

    return 0


def search_url_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc search-url")
    parser.add_argument("software")
    parser.add_argument("version", nargs="?", default="latest")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    return search_url(args.software, args.version,
                       getattr(args, "project_dir", None))
