#!/usr/bin/env python3
"""mINI 0.9.20 交付形态自检（M1–M13）。

判据全部是**外部可核对真值**：交付头文件/许可证的 sha256 来自上游
0.9.20 tarball（与 conandata.yml 里同一份制品），版本号来自被测 conan
ref，消费者契约来自 conan 实际生成的 CMake/pkg-config 文件。

用法: test_mini_shape.py <package_folder> <generators_folder> <version> [cxx]
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

# 上游 0.9.20 tarball 中 src/mini/ini.h 与 LICENSE 的 sha256（sha256sum 实测）
UPSTREAM_HEADER_SHA256 = \
    "35857afbb7d42b742d58c1cad5ab301fdb89c2367da01cb6e4609d6d6cf76b5e"
UPSTREAM_LICENSE_SHA256 = \
    "e8164252c3414652447418b5e9b40a31c3ba7cd1a21e235c23a3192c87cf7649"

RESULTS = []


def record(name, passed, detail=""):
    RESULTS.append((name, bool(passed), detail))
    print(("ok   " if passed else "FAIL ") + name + (" | " + detail if detail else ""))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_cxx(hint):
    candidates = [hint, os.environ.get("CXX", ""),
                  "/data/service/hnp/bin/clang++",
                  shutil.which("clang++") or "", shutil.which("g++") or "",
                  shutil.which("c++") or ""]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return ""


def compile_and_run(cxx, include_dir, workdir, source, tag):
    src = os.path.join(workdir, "probe_%s.cpp" % tag)
    binary = os.path.join(workdir, "probe_%s" % tag)
    with open(src, "w", encoding="utf-8") as handle:
        handle.write(source)
    build = subprocess.run([cxx, "-std=c++17", "-Wall", "-I" + include_dir,
                            src, "-o", binary],
                           cwd=workdir, capture_output=True, text=True)
    if build.returncode != 0:
        return False, "compile rc=%d %s" % (build.returncode,
                                            build.stderr.strip()[:300])
    run = subprocess.run([binary], cwd=workdir, capture_output=True, text=True)
    if run.returncode != 0:
        return False, "run rc=%d %s" % (run.returncode, run.stderr.strip()[:300])
    return True, run.stdout.strip()


REUSE_PROBE = r'''
#include "mini/ini.h"
#include <fstream>
#include <iostream>
int main() {
    std::ofstream("probe.ini") << "[sec]\nkey = value\n";
    mINI::INIFile file("probe.ini");
    mINI::INIStructure ini;
    if (!file.read(ini)) { std::cout << "read failed" << std::endl; return 1; }
    if (ini["sec"]["key"] != "value") { std::cout << "value mismatch" << std::endl; return 2; }
    // 大小写不敏感查询（上游 README 声明）
    if (ini["SEC"]["KEY"] != "value") { std::cout << "case mismatch" << std::endl; return 3; }
    std::cout << "probe ok " << ini["sec"]["key"] << std::endl;
    return 0;
}
'''

DOUBLE_INCLUDE_PROBE = r'''
#include "mini/ini.h"
#include "mini/ini.h"
#include <iostream>
int main() {
    mINI::INIStructure ini;
    ini["a"]["b"] = "c";
    std::cout << "double include ok " << ini["a"]["b"] << std::endl;
    return 0;
}
'''


def main():
    pkg = os.path.abspath(sys.argv[1])
    gens = os.path.abspath(sys.argv[2])
    version = sys.argv[3]
    cxx_hint = sys.argv[4] if len(sys.argv) > 4 else ""
    include_dir = os.path.join(pkg, "include")
    header = os.path.join(include_dir, "mini", "ini.h")
    license_file = os.path.join(pkg, "licenses", "LICENSE")

    # M1 交付头文件与上游字节一致
    header_ok = os.path.isfile(header)
    header_sha = sha256_file(header) if header_ok else "MISSING"
    record("M1 交付 include/mini/ini.h 的 sha256 == 上游 src/mini/ini.h",
           header_ok and header_sha == UPSTREAM_HEADER_SHA256,
           "sha256=%s size=%s" % (header_sha,
                                  os.path.getsize(header) if header_ok else "-"))

    # M2 include/ 交付清单
    listing = sorted(
        os.path.relpath(os.path.join(root, name), include_dir).replace("\\", "/")
        for root, _dirs, files in os.walk(include_dir) for name in files)
    record("M2 include/ 交付清单恰为 ['mini/ini.h']",
           listing == ["mini/ini.h"], repr(listing))

    # M3 header-only 不交付任何二进制/可执行文件
    binary_suffix = (".so", ".a", ".o", ".dll", ".dylib", ".lib", ".exe")
    binaries = [f for f in listing if f.endswith(binary_suffix)]
    execbits = [f for f in listing if os.access(os.path.join(include_dir, f), os.X_OK)]
    has_bin_dir = os.path.isdir(os.path.join(pkg, "bin"))
    record("M3 无 bin/、无 .so/.a/.o、无可执行位交付文件（header-only）",
           not binaries and not execbits and not has_bin_dir,
           "binaries=%s execbits=%s bin_dir=%s" % (binaries, execbits, has_bin_dir))

    # M4 许可证与上游字节一致
    license_ok = os.path.isfile(license_file)
    license_sha = sha256_file(license_file) if license_ok else "MISSING"
    record("M4 licenses/LICENSE 的 sha256 == 上游 LICENSE",
           license_ok and license_sha == UPSTREAM_LICENSE_SHA256,
           "sha256=%s" % license_sha)

    # M5 无隐藏文件 / 构建残留（JC5 口径）
    all_files = sorted(
        os.path.relpath(os.path.join(root, name), pkg).replace("\\", "/")
        for root, _dirs, files in os.walk(pkg) for name in files)
    junk = [f for f in all_files
            if f.startswith(".") or "/." in f or "__pycache__" in f
            or f.endswith((".pyc", ".bak", ".orig", ".rej"))
            or os.path.basename(f) in ("conanbuild.sh", "conanrun.sh",
                                       "conanbuild.bat", "conanrun.bat",
                                       "deactivate_conanbuild.sh")]
    record("M5 包内无隐藏文件/构建脚本残留/__pycache__（JC5 口径）",
           not junk, "junk=%s all=%s" % (junk, all_files))

    # M6 交付头文件不含本机构建/缓存绝对路径（源码树泄漏）
    leaked = []
    if header_ok:
        text = open(header, encoding="utf-8", errors="replace").read()
        for pattern in ("/.conan2", "/conan/data", "/tmp/", "/mnt/", "/home/",
                        "/data/", pkg):
            if pattern in text:
                leaked.append(pattern)
    record("M6 交付头文件不含构建/缓存绝对路径字面量", not leaked, "leaked=%s" % leaked)

    # M7 CMakeDeps 契约：find_package(mINI) -> mINI::mINI
    cmake_files = []
    if os.path.isdir(gens):
        cmake_files = sorted(f for f in os.listdir(gens) if f.endswith(".cmake"))
    cmake_text = ""
    for name in cmake_files:
        cmake_text += open(os.path.join(gens, name), encoding="utf-8",
                           errors="replace").read()
    config_name = [f for f in cmake_files
                   if f.lower().replace("-", "").startswith("miniconfig")]
    record("M7 CMake 契约：mINIConfig.cmake 存在且定义 mINI::mINI 目标",
           bool(config_name) and "add_library(mINI::mINI" in cmake_text
           and "mINI::mINI" in cmake_text,
           "config=%s targets_defined=%s" % (config_name,
                                             "add_library(mINI::mINI" in cmake_text))

    # M8 CMake 契约指向本包 include（装配自洽）
    normalized_include = include_dir.replace("\\", "/")
    record("M8 CMake 契约的 INTERFACE_INCLUDE_DIRECTORIES 指向本包 include/",
           normalized_include in cmake_text and "INTERFACE_INCLUDE_DIRECTORIES"
           in cmake_text,
           "needle=%s" % normalized_include)

    # M9 PkgConfigDeps 契约：mini.pc 可重定位
    pc = os.path.join(gens, "mini.pc")
    pc_text = open(pc, encoding="utf-8", errors="replace").read() if os.path.isfile(pc) else ""
    pc_prefix = re.search(r"^prefix=(.+)$", pc_text, re.M)
    record("M9 pkg-config 契约：mini.pc 存在，Name/Version/prefix 正确且 Cflags 用 ${includedir}",
           os.path.isfile(pc)
           and re.search(r"^Name: *mini\s*$", pc_text, re.M) is not None
           and re.search(r"^Version: *" + re.escape(version) + r"\s*$", pc_text, re.M) is not None
           and pc_prefix is not None
           and os.path.normpath(pc_prefix.group(1).strip()) == os.path.normpath(pkg)
           and "includedir=${prefix}/include" in pc_text
           and "${includedir}" in pc_text,
           "prefix=%s" % (pc_prefix.group(1) if pc_prefix else "MISSING"))

    # M10 真实调用 pkg-config 复核契约可用性
    pkgconfig = shutil.which("pkg-config") or ""
    detail = "pkg-config not found"
    pc_ok = False
    if pkgconfig:
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = gens
        probe = subprocess.run([pkgconfig, "--modversion", "mini"],
                               capture_output=True, text=True, env=env)
        flags = subprocess.run([pkgconfig, "--cflags", "mini"],
                               capture_output=True, text=True, env=env)
        detail = "modversion=%s cflags=%s" % (probe.stdout.strip(), flags.stdout.strip())
        pc_ok = (probe.returncode == 0 and probe.stdout.strip() == version
                 and flags.returncode == 0
                 and normalized_include in flags.stdout.replace("\\", "/"))
    record("M10 pkg-config --modversion/--cflags mini 输出正确路径与版本", pc_ok, detail)

    # M11 可重定位：把 include/ 搬到临时目录后仍能编译+运行真实 API
    cxx = find_cxx(cxx_hint)
    tmp = tempfile.mkdtemp(prefix="mini-reloc-")
    reloc_ok, reloc_detail = False, "no C++ compiler found"
    if cxx:
        try:
            shutil.copytree(include_dir, os.path.join(tmp, "include"))
            reloc_ok, reloc_detail = compile_and_run(
                cxx, os.path.join(tmp, "include"), tmp, REUSE_PROBE, "reloc")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    record("M11 搬迁 include/ 到临时目录后编译+运行成功（可重定位 + 真实取值）",
           reloc_ok, "cxx=%s %s" % (cxx or "-", reloc_detail))

    # M12 头文件 include guard：同一 TU 连续 include 两次可编译运行
    tmp2 = tempfile.mkdtemp(prefix="mini-guard-")
    guard_ok, guard_detail = False, "no C++ compiler found"
    if cxx:
        try:
            guard_ok, guard_detail = compile_and_run(
                cxx, include_dir, tmp2, DOUBLE_INCLUDE_PROBE, "guard")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    record("M12 同一 TU 连续 include mini/ini.h 两次可编译运行（include guard）",
           guard_ok, guard_detail)

    # M13 版本一致性：pkg-config / CMake 版本文件 / 被测 conan ref 三者一致
    cmake_version = re.search(r'PACKAGE_VERSION "([^"]+)"', cmake_text)
    pc_version = re.search(r"^Version: *(.+?)\s*$", pc_text, re.M)
    record("M13 版本三处一致（被测 ref / mini.pc / mINI-config-version.cmake）",
           bool(cmake_version) and bool(pc_version)
           and cmake_version.group(1) == version
           and pc_version.group(1) == version,
           "ref=%s pc=%s cmake=%s" % (version,
                                      pc_version.group(1) if pc_version else "-",
                                      cmake_version.group(1) if cmake_version else "-"))

    failed = [name for name, passed, _ in RESULTS if not passed]
    print("-" * 60)
    print("M 自检: %d/%d 通过" % (len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print("失败项: " + ", ".join(failed))
        return 1
    print("ALL DELIVERY SHAPE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
