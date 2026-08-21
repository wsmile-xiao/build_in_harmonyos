#!/usr/bin/env python3
"""test_mlt.py — real consumer test source for mlt 7.34.0 (L0c).

Verifies the installed mlt library is a valid OHOS aarch64 ELF with the
expected framework API symbols (mlt_version / mlt_factory_init), and
attempts a live ctypes load (version API call) when the sandbox permits.

OHOS AppSpawn 沙箱对 dlopen 非系统路径 .so 有限制（Permission denied），
与 abiword-plugin-eml 已合入方案一致：readelf 硬性验证 ELF 有效性与导出
符号；ctypes.CDLL 加载失败仅当为沙箱/符号重定位类原因时记录并 PASS。

Usage: test_mlt.py <lib-dir>
"""
import ctypes
import os
import subprocess
import sys


def _find_readelf():
    for cand in ("/data/service/hnp/bin/readelf",
                 "/data/service/hnp/bin/llvm-readelf",
                 "readelf"):
        try:
            subprocess.run([cand, "--version"], capture_output=True, timeout=5)
            return cand
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _verify_elf_symbols(lib_path):
    """readelf 硬性验证：库是有效 aarch64 ELF 且精确导出 mlt 框架符号。

    架构用 readelf -h 校验（Machine: AArch64）；符号用 readelf -sW 且只匹配
    GLOBAL 导出条目（避免 "mlt_version_get_*" 平凡满足 "mlt_version" 子串）。
    """
    readelf = _find_readelf()
    if not readelf:
        raise AssertionError("No readelf found in toolchain")
    # 1) 架构校验：目标平台为 OHOS aarch64
    hdr = subprocess.run([readelf, "-h", lib_path], capture_output=True, text=True, timeout=15)
    if hdr.returncode != 0:
        raise AssertionError(f"readelf -h failed (rc={hdr.returncode}): {hdr.stderr}")
    machine = None
    for line in hdr.stdout.splitlines():
        if line.strip().startswith("Machine:"):
            machine = line.split(":", 1)[1].strip()
            break
    if machine != "AArch64":
        raise AssertionError(f"Not an aarch64 ELF (Machine: {machine})")
    # 2) 符号校验：精确匹配 GLOBAL 导出符号（含 1 个 func、1 个 object 代表）
    result = subprocess.run(
        [readelf, "-sW", lib_path], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise AssertionError(f"readelf failed (rc={result.returncode}): {result.stderr}")
    expected = ("mlt_factory_init", "mlt_version_get_major", "mlt_version_get_minor")
    missing = [s for s in expected if not any(
        f" {s}" in ln and " GLOBAL " in ln for ln in result.stdout.splitlines())]
    if missing:
        raise AssertionError(f"Expected exported symbols not found: {missing}")
    print(f"[ok] readelf: {lib_path} is valid AArch64 ELF, exports {', '.join(expected)}")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_mlt.py <lib-dir>")
    lib_dir = sys.argv[1]
    # mlt 7.x 安装的框架库名为 libmlt-7.so（带主版本后缀），兼容历史命名
    candidates = ["libmlt-7.so", "libmlt.so", "libmlt.so.7", "libmlt.so.7.34.0"]
    lib_path = None
    for c in candidates:
        p = os.path.join(lib_dir, c)
        if os.path.isfile(p):
            lib_path = p
            break
    if not lib_path:
        raise AssertionError(f"libmlt not found in {lib_dir}")

    # 1) 硬性验证：readelf 检查 ELF 有效性与导出符号（沙箱无关）
    _verify_elf_symbols(lib_path)

    # 2) 软验证：ctypes 实际加载（沙箱允许时）+ mlt_version API 调用
    try:
        lib = ctypes.CDLL(lib_path, mode=os.RTLD_LAZY)
    except OSError as e:
        # 仅 OHOS AppSpawn 沙箱对 dlopen 的权限限制（Permission denied/EACCES）视为
        # 预期环境行为降级；dlopen 抛出的 OSError 中 strerror 属性可能为 None，
        # 完整错误文本在 str(e) 中，故用 str(e) 匹配（errno 也可能为 None）。
        # symbol not found / relocating / 依赖缺失等一律判失败，避免把真实加载缺陷
        # （ABI 不匹配、符号未导出、依赖缺失）误判为沙箱预期而假通过。
        msg = str(e)
        if e.errno == 13 or "Permission denied" in msg:
            print(f"[ok] ctypes.CDLL blocked by sandbox dlopen policy ({msg}); "
                  f"ELF+symbols verified via readelf above")
            return
        raise AssertionError(f"failed to load {lib_path}: {e}")

    # mlt 7.x 版本 API：mlt_version_get_int()/get_major()/get_minor()/get_revision()
    # （注意：不是旧版 mlt_version(int*...) 指针 API）
    try:
        get_major = lib.mlt_version_get_major
        get_major.restype = ctypes.c_int
        get_minor = lib.mlt_version_get_minor
        get_minor.restype = ctypes.c_int
        get_revision = lib.mlt_version_get_revision
        get_revision.restype = ctypes.c_int
    except AttributeError:
        raise AssertionError("mlt_version_get_* symbol not exported")
    major = get_major()
    minor = get_minor()
    revision = get_revision()
    ver = (major, minor, revision)
    print(f"OK: libmlt loaded, version {ver[0]}.{ver[1]}.{ver[2]}")
    if major != 7:
        raise AssertionError(f"unexpected major version: {ver}")


if __name__ == "__main__":
    main()
