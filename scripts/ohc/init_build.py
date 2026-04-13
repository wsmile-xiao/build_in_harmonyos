"""Init-build pipeline — download, extract, scaffold, environment check.
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail
from .check_env import check_env
from .init_archive import init_archive
from .search_url import search_url
from .dependency_resolver import get_missing_deps, resolve_and_install

# HarmonyOS 环境可能缺少 CA 证书，创建不验证的 SSL context
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
_ssl_env = {"SSL_CONTEXT": "1"}  # marker for _urlopen helper


def _urlopen(req, timeout=300, context=None):
    """urlopen with fallback to no-SSL-verify for HarmonyOS."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        if "CERTIFICATE" in str(e) or "SSL" in str(e):
            ctx = context or _SSL_CTX
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise


def _sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._+-]', '', s)


def _load_registry(project_dir: Path) -> dict:
    """Simple YAML parser for software-registry.yaml."""
    reg_file = project_dir / "scripts" / "software-registry.yaml"
    if not reg_file.exists():
        return {}
    registry: dict[str, dict] = {}
    content = reg_file.read_text(encoding="utf-8", errors="replace")
    in_entry = None
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Top-level entry: "  name:" inside "registry:"
        m = re.match(r'^  (\S+):\s*$', line)
        if m and not line.startswith("    "):
            in_entry = m.group(1)
            registry[in_entry] = {}
            continue
        if in_entry and line.startswith("    "):
            kv = re.match(r'^    (\w+):\s*(.*)', line)
            if kv:
                key, val = kv.group(1), kv.group(2).strip().strip('"').strip("'")
                if val:
                    registry[in_entry][key] = val
                else:
                    registry[in_entry][key] = ""
            # Handle list values (known_issues, etc.)
            elif line.strip().startswith("- "):
                registry[in_entry].setdefault("_list", [])
                registry[in_entry]["_list"].append(line.strip()[2:])
    return registry


def _guess_build_system(url: str) -> str:
    u = url.lower()
    if "cmake.org" in u or "cmake" in u:
        return "cmake"
    if "mesonbuild" in u:
        return "meson"
    if "openssl" in u or "python" in u:
        return "custom"
    return "autotools"


def _guess_tar_format(url: str) -> str:
    for fmt in ["tar.xz", "tar.bz2", "tar.gz", "zip"]:
        if url.endswith(fmt):
            return fmt
    return "tar.gz"


def _verify_checksum(filepath: Path, expected: str) -> int:
    if not expected:
        return 0
    actual = hashlib.sha256(filepath.read_bytes()).hexdigest()
    if actual == expected:
        return 0
    filepath.unlink(missing_ok=True)
    return 1


def _download_one(url: str, dest: Path) -> int:
    """Download a single URL to dest. Returns 0=ok, 1=fail."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    log_info(f"  下载: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ohc/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            with open(dest, 'wb') as f:
                while True:
                    chunk = resp.read(65536)  # 64KB chunks for speed
                    if not chunk:
                        break
                    f.write(chunk)
        return 0
    except Exception as e:
        log_fail(f"  下载失败 ({url}): {e}")
        if dest.exists():
            dest.unlink()
        return 1


def _download(urls: list[str], dest: Path) -> int:
    """Download from multiple URLs concurrently. First success wins.
    Uses asyncio + urllib for parallel HEAD probing, then sequential download."""
    if len(urls) == 1:
        return _download_one(urls[0], dest)

    # Probe all URLs in parallel to find fastest available
    import asyncio

    async def _probe(session_url: str) -> tuple[str, bool]:
        loop = asyncio.get_event_loop()
        try:
            req = urllib.request.Request(session_url, method="HEAD",
                                          headers={"User-Agent": "ohc/1.0"})
            def _head():
                try:
                    _urlopen(req, timeout=15)
                    return True
                except Exception:
                    return False
            ok = await loop.run_in_executor(None, _head)
            return session_url, ok
        except Exception:
            return session_url, False

    async def _probe_all():
        tasks = [_probe(u) for u in urls]
        return await asyncio.gather(*tasks)

    try:
        results = asyncio.run(_probe_all())
    except RuntimeError:
        # No event loop (e.g. nested), fallback to sequential
        results = [(u, True) for u in urls]

    # Try URLs in order: probed-available first, then the rest
    available = [u for u, ok in results if ok]
    order = available + [u for u in urls if u not in available]

    for url in order:
        rc = _download_one(url, dest)
        if rc == 0:
            return 0
    return 1


def _extract(tarball: Path, dest: Path, fmt: str) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        if fmt == "zip":
            with zipfile.ZipFile(tarball) as zf:
                zf.extractall(dest)
        else:
            mode = {"tar.gz": "r:gz", "tar.xz": "r:xz", "tar.bz2": "r:bz2"}.get(fmt, "r:gz")
            with tarfile.open(tarball, mode) as tf:
                tf.extractall(dest)
        # Handle subdirectory promotion (single level)
        children = list(dest.iterdir())
        if len(children) == 1 and children[0].is_dir():
            sub = children[0]
            for item in sub.iterdir():
                shutil.move(str(item), dest / item.name)
            sub.rmdir()
        return True
    except Exception as e:
        log_fail(f"  解压失败: {e}")
        return False


# ---------- F068: nested source directory detection ----------

_BUILD_MARKERS = ("configure", "CMakeLists.txt", "Makefile", "meson.build")


def _has_build_marker(directory: Path) -> bool:
    """Return True if *directory* directly contains a known build-system file."""
    return any((directory / m).exists() for m in _BUILD_MARKERS)


def _find_source_subdir(directory: Path, max_depth: int = 3) -> Path | None:
    """Recursively search for the shallowest subdirectory with a build marker.

    Skips hidden directories (starting with ``.``).  Returns ``None`` when
    no suitable directory is found within *max_depth* levels.
    """
    if _has_build_marker(directory):
        return directory
    if max_depth <= 0:
        return None
    for child in sorted(directory.iterdir()):
        if child.is_dir() and not child.name.startswith('.'):
            result = _find_source_subdir(child, max_depth - 1)
            if result is not None:
                return result
    return None


def _promote_nested_source(directory: Path, max_depth: int = 3) -> bool:
    """Detect and fix deeply nested source trees.

    Some tarballs unpack into multiple layers of wrapper directories
    (e.g. ``pkg-1.0/pkg-1.0/``).  The built-in single-level promotion in
    :func:`_extract` may not be sufficient.  This function checks whether
    *directory* contains a build marker and, if not, searches up to
    *max_depth* levels for a subdirectory that does, then promotes its
    contents to *directory*.

    Returns ``True`` if a promotion was performed, ``False`` otherwise.
    Dot-files (e.g. ``.tarball-sha256``) in *directory* are preserved.
    """
    if _has_build_marker(directory):
        return False

    source = _find_source_subdir(directory, max_depth)
    if source is None or source == directory:
        log_warn(f"  嵌套源码检测: 未在 {directory} 及其 {max_depth} 层子目录中找到构建文件")
        return False

    rel = source.relative_to(directory)
    log_info(f"  嵌套源码检测: 找到源码在 {rel}，正在提升到 {directory.name} ...")

    # Use a temporary location outside *directory* so moves are safe
    tmp_dir = directory.parent / (directory.name + ".__promote_tmp__")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1) Move every item from *source* into the temp dir
    for item in list(source.iterdir()):
        shutil.move(str(item), tmp_dir / item.name)

    # 2) Remove remaining items in *directory* (intermediate wrapper dirs)
    for item in list(directory.iterdir()):
        if item == tmp_dir:
            continue
        # Preserve dot-files at the directory root (e.g. .tarball-sha256)
        if item.name.startswith('.') and item.is_file():
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    # 3) Move everything back from temp to *directory*
    for item in list(tmp_dir.iterdir()):
        shutil.move(str(item), directory / item.name)

    # 4) Clean up temp dir
    try:
        tmp_dir.rmdir()
    except OSError:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    log_ok(f"  嵌套源码提升完成: {rel} → {directory.name}")
    return True


# ---------- end F068 ----------


def _create_dual_track(orig_dir: Path, work_dir: Path,
                       tarball: Path, fmt: str) -> int:
    """Create .orig (read-only baseline) and .work (writable copy)."""
    # Check if orig exists and is valid
    orig_valid = (orig_dir.exists() and
                  any((orig_dir / f).exists() for f in
                      ["configure", "CMakeLists.txt", "Makefile", "meson.build"]))

    if not orig_valid:
        if orig_dir.exists():
            shutil.rmtree(orig_dir)
        if not _extract(tarball, orig_dir, fmt):
            return 3
        # Write SHA256 marker
        sha = hashlib.sha256(tarball.read_bytes()).hexdigest()
        (orig_dir / ".tarball-sha256").write_text(sha, encoding="utf-8")
        # F068: promote deeply nested source if needed
        _promote_nested_source(orig_dir)
        log_ok(f"  .orig 已解压: {orig_dir}")
    else:
        log_ok(f"  .orig 已存在: {orig_dir}")

    # Create work directory
    work_valid = (work_dir.exists() and
                  any((work_dir / f).exists() for f in
                      ["configure", "CMakeLists.txt", "Makefile", "meson.build"]))
    if not work_valid:
        if work_dir.exists():
            shutil.rmtree(work_dir)
        try:
            shutil.copytree(orig_dir, work_dir, copy_function=os.link)
            # Remove marker from work copy
            (work_dir / ".tarball-sha256").unlink(missing_ok=True)
            log_ok(f"  .work 已创建 (硬链接): {work_dir}")
        except OSError:
            # HMDFS may reject hard-links; clean partial dir then fallback to copy
            if work_dir.exists():
                shutil.rmtree(work_dir)
            shutil.copytree(orig_dir, work_dir)
            log_ok(f"  .work 已创建 (复制): {work_dir}")
        # F068: ensure work_dir also has build markers at top level
        _promote_nested_source(work_dir)
    else:
        log_ok(f"  .work 已存在: {work_dir}")

    return 0


def _generate_context(path: Path, **kw) -> None:
    """Generate .build-context file."""
    prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
    tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
    lines = [
        f"# BUILD CONTEXT — {kw['software']} {kw['version']}",
        f"# 由 init_build.py 自动生成",
        "",
        f"export BUILD_SOFTWARE=\"{kw['software']}\"",
        f"export BUILD_VERSION=\"{kw['version']}\"",
        f"export BUILD_SYSTEM=\"{kw['build_system']}\"",
        f"export BUILD_MODE=\"{kw.get('mode', 'auto')}\"",
        "",
        f"export DEFAULT_PREFIX=\"{prefix}\"",
        f"export TEST_PREFIX=\"{tmpdir}/test-install-{kw['software']}-{kw['version']}\"",
        "",
        f"export BUILD_TARBALL=\"{kw['tarball_path']}\"",
        f"export BUILD_SRC_DIR=\"{kw['work_dir']}\"",
        f"export BUILD_SRC_ORIG_DIR=\"{kw['orig_dir']}\"",
        f"export BUILD_ARCHIVE_DIR=\"{kw['archive_dir']}\"",
        f"export BUILD_CONTEXT_FILE=\"{path}\"",
        "",
        f"export BUILD_URL=\"{kw.get('download_url', '')}\"",
        f"export BUILD_TAR_FORMAT=\"{kw.get('tar_format', 'tar.gz')}\"",
        "",
        f"export BUILD_HISTORY_FOUND=\"{kw.get('history_found', False)}\"",
        f"export BUILD_HISTORY_STATUS=\"{kw.get('history_status', '')}\"",
        f"export BUILD_HISTORY_CONFIGURE_OPTIONS=\"{kw.get('history_configure_options', '')}\"",
        "",
        f"# 下一步: python3 ohc-run.py build {kw['software']} {kw['version']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def init_build(software: str, version: str = "", mode: str = "auto",
               url: str = "", tar: str = "", no_download: bool = False,
               force: bool = False, pdir: str | None = None) -> int:
    project = Path(pdir) if pdir else Path(find_project_dir())
    build_dir = Path(os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))) / "builds"

    software = _sanitize(software)
    version = _sanitize(version)

    if not software:
        log_fail("缺少软件名称"); return 1

    # --resume mode
    if mode == "resume":
        ctx_files = sorted(project.glob(".build-context-*"))
        if not ctx_files:
            log_fail("找不到 .build-context 文件"); return 2
        print(ctx_files[-1].read_text(encoding="utf-8"))
        return 0

    log_info(f"🚀 初始化编译: {software} {version or '(latest)'}")

    # Step 1: Registry lookup
    registry = _load_registry(project)
    entry = registry.get(software, {})
    in_registry = bool(entry)

    if not version:
        version = entry.get("latest_version", "")
    if not version and not url:
        if not in_registry:
            search_url(software, "latest", pdir=str(project))
        return 1

    # Step 2: Determine URL
    download_url = url
    if not download_url:
        tmpl = entry.get("url_template", "")
        if tmpl and "{version}" in tmpl:
            download_url = tmpl.replace("{version}", version)
        elif tmpl:
            download_url = tmpl
        else:
            fb = entry.get("url_fallback", "")
            if fb:
                download_url = fb.replace("{version}", version)
            elif not in_registry:
                search_url(software, version, pdir=str(project))
                return 1
            else:
                log_fail("注册表条目缺少 URL"); return 3

    build_system = entry.get("build_system", "") or _guess_build_system(download_url)
    tar_format = tar or entry.get("tar_format", "") or _guess_tar_format(download_url)

    # Step 3: Download
    tarball = build_dir / f"{software}-{version}.{tar_format}"
    orig_dir = build_dir / f"{software}-{version}.orig"
    work_dir = build_dir / f"{software}-{version}.work"

    if no_download:
        if not work_dir.is_dir() and not orig_dir.is_dir():
            log_fail(f"源码目录不存在: {work_dir}"); return 2
    else:
        build_dir.mkdir(parents=True, exist_ok=True)
        if not tarball.exists():
            urls = [download_url]
            fb = entry.get("url_fallback", "")
            if fb:
                urls.append(fb.replace("{version}", version))
            rc = _download(urls, tarball)
            if rc != 0:
                log_fail("下载失败"); return 3
            # HTML detection
            if tarball.exists():
                head = tarball.read_bytes()[:200].decode("utf-8", errors="ignore")
                if "<!DOCTYPE" in head or "<html" in head:
                    tarball.unlink(); log_fail("下载内容是 HTML"); return 3
        else:
            log_ok(f"  tarball 已存在: {tarball.stat().st_size // 1024}KB")

        # SHA256 check
        expected = entry.get("checksum_sha256", "") or os.environ.get("EXPECTED_SHA256", "")
        if _verify_checksum(tarball, expected) != 0:
            log_fail("SHA256 校验未通过"); return 3

    # Step 4: Dual-track extraction
    if force and work_dir.exists():
        shutil.rmtree(work_dir)
    rc = _create_dual_track(orig_dir, work_dir, tarball, tar_format)
    if rc != 0:
        return rc

    # Step 5: Check history + validate parameters (R15)
    archive_dir = project / "archives" / software[0].lower() / software / version
    history_found = archive_dir.is_dir()
    history_status = ""
    history_configure_options: list[str] = []
    if history_found:
        mf = archive_dir / "manifest.yaml"
        if mf.exists():
            in_options = False
            for line in mf.read_text(encoding="utf-8", errors="replace").split("\n"):
                stripped = line.strip()
                if stripped.startswith("status:"):
                    history_status = line.split(":", 1)[1].strip()
                elif stripped.startswith("configure_options:"):
                    in_options = True
                elif in_options:
                    if line.startswith("    - "):
                        history_configure_options.append(stripped[2:].strip())
                    elif not line.startswith(" "):
                        in_options = False
        log_info(f"  历史档案: {history_status or 'unknown'}")

        # R15: Validate history configure parameters
        _FORBIDDEN_PARAMS = ["--build=", "--host=", "--target="]
        _DANGER_PARAMS = {"ncurses": ["--without-shared"],
                          "openssl": ["--no-asm"],
                          "bash": ["--without-bash-malloc"]}
        forbidden_found = []
        for fp in _FORBIDDEN_PARAMS:
            if any(fp in opt for opt in history_configure_options):
                forbidden_found.append(fp.rstrip("="))
        danger_missing = []
        for dp in _DANGER_PARAMS.get(software, []):
            if not any(dp in opt for opt in history_configure_options):
                danger_missing.append(dp)

        if forbidden_found:
            log_warn(f"  ⚠️ R15: 历史参数包含禁用项: {', '.join(forbidden_found)}")
            log_warn(f"     本平台为 native 编译，禁止 --build/--host/--target")
            log_warn(f"     正确做法: 修改 config.guess/config.sub（见 E007）")
        if danger_missing:
            log_warn(f"  ⚠️ R15: 历史参数缺少危险库参数: {', '.join(danger_missing)}")
        if not forbidden_found and not danger_missing and history_configure_options:
            log_ok(f"  ✅ 历史参数验证通过 ({len(history_configure_options)} 项)")
        elif not history_configure_options:
            log_warn(f"  ⚠️ R15: 历史记录无 configure_options（可能为旧格式）")

    # Step 6: Scaffold archive
    need_scaffold = True
    if history_found:
        prog = archive_dir / "PROGRESS.md"
        mf = archive_dir / "manifest.yaml"
        if prog.exists() and len(prog.read_text(encoding="utf-8", errors="replace").splitlines()) > 15:
            if mf.exists() and len(mf.read_text(encoding="utf-8", errors="replace").splitlines()) > 10:
                need_scaffold = False

    if need_scaffold:
        init_archive(software, version, download_url, build_system, pdir=str(project))

    # Step 7: Dependency resolution
    log_info("检查编译依赖...")
    prefix = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
    missing = get_missing_deps(software, prefix)
    if missing:
        missing_prebuilt = [d for d in missing if resolve_and_install.__module__ and True]
        log_warn(f"  缺失依赖: {', '.join(missing)}")
        # 尝试自动安装有预编译包的依赖
        rc = resolve_and_install(software, version, prefix, dry_run=False)
        if rc != 0:
            log_warn("  ⚠️ 部分依赖无法自动安装，编译可能会失败")
            log_warn("  提示: 手动安装预编译包 → ohc-run.py resolve-deps --install <name>")
    else:
        log_ok("  所有依赖已就绪")

    # Step 8: Environment check
    check_env()

    # Step 9: Generate context file
    ctx_file = project / f".build-context-{software}-{version}"
    _generate_context(
        ctx_file,
        software=software, version=version, build_system=build_system,
        mode=mode, tarball_path=tarball, work_dir=work_dir,
        orig_dir=orig_dir, archive_dir=archive_dir,
        download_url=download_url, tar_format=tar_format,
        history_found=history_found, history_status=history_status,
        history_configure_options=" ".join(history_configure_options),
    )
    log_ok(f"✅ 上下文文件: {ctx_file.name}")
    log_ok(f"   源码: {work_dir}")
    log_ok(f"   归档: {archive_dir}")
    return 0


def init_build_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc init-build",
        description="编译初始化: registry→URL→download→extract→scaffold→env-check")
    parser.add_argument("software")
    parser.add_argument("version", nargs="?", default="")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--auto", action="store_const", const="auto", dest="mode")
    mode.add_argument("--ask", action="store_const", const="ask", dest="mode")
    mode.add_argument("--resume", action="store_const", const="resume", dest="mode")
    parser.add_argument("--url")
    parser.add_argument("--tar", choices=["tar.gz", "tar.xz", "tar.bz2", "zip"])
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--project-dir")
    parser.set_defaults(mode="auto")
    args = parser.parse_args(argv)
    return init_build(args.software, args.version, args.mode,
                       args.url or "", args.tar or "",
                       args.no_download, args.force,
                       getattr(args, "project_dir", None))
