#!/usr/bin/env python3
"""test_ohos — gplotpp 1.1.0 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T4  真实制图：消费者程序通过已安装的 gplot++.h + Gnuplot API 输出
      "dumb" 终端渲染文件，并验证系列/坐标轴标签真实出现

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile


def resolve_cc():
    """Resolve a real clang executable.

    The shell environment may set CC=clang with no such binary on PATH
    (OHOS toolchain lives under /data/service/hnp/bin). Prefer a CC that
    actually exists, then the OHOS SDK clang, then plain clang.
    """
    candidates = [
        os.environ.get("CC", ""),
        "/data/service/hnp/bin/clang",
        "clang",
    ]
    for cand in candidates:
        if not cand:
            continue
        if os.path.isfile(cand):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return "clang"


def resolve_cxx():
    """Resolve a real clang++ executable (C++ driver links libc++).

    The consumer source is C++; using the C driver (clang) would leave
    libc++/libc++abi undefined at link time. Prefer a CXX that actually
    exists, then the OHOS SDK clang++, then plain clang++.
    """
    candidates = [
        os.environ.get("CXX", ""),
        "/data/service/hnp/bin/clang++",
        "clang++",
    ]
    for cand in candidates:
        if not cand:
            continue
        if os.path.isfile(cand):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return "clang++"


def resolve_tool(env_name, candidates):
    """Resolve a binutils-style tool (readelf/strings) with fallbacks."""
    first = os.environ.get(env_name, "")
    for cand in [first] + candidates:
        if not cand:
            continue
        if os.path.isfile(cand):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return candidates[0]


CXX = resolve_cxx()
READELF = resolve_tool("READELF", ["/data/service/hnp/bin/readelf", "readelf"])
STRINGS = resolve_tool("STRINGS", ["/data/service/hnp/bin/strings", "strings"])

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"gplotpp-1.1.0"]

TEST_CXX = r"""
#include <chrono>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include "gplot++.h"

int main() {
    const std::string out_file{"ohos_plot.svg"};
    {
        Gnuplot plt{};
        if (!plt.redirect_to_svg(out_file, "800,600")) {
            return 1;
        }
        std::vector<double> x{1, 2, 3, 4, 5};
        std::vector<double> y{5, 4, 3, 2, 1};
        plt.plot(x, y, "OHOSSeries", Gnuplot::LineStyle::POINTS);
        plt.set_xlabel("OHOSX");
        plt.set_ylabel("OHOSY");
        if (!plt.show()) {
            return 2;
        }
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(1200));
    std::ifstream in(out_file.c_str(), std::ios::binary);
    std::stringstream ss;
    ss << in.rdbuf();
    const std::string content = ss.str();
    if (content.empty()) {
        return 3;
    }
    if (content.find("OHOSSeries") == std::string::npos) {
        return 4;
    }
    if (content.find("OHOSX") == std::string::npos ||
        content.find("OHOSY") == std::string::npos) {
        return 5;
    }
    return 0;
}
"""


def find_gnuplot_bin():
    import glob
    import shutil

    found = shutil.which("gnuplot")
    if found and os.path.isfile(found):
        return found
    home = os.path.expanduser("~")
    # HMDFS ignores chmod → os.access(X_OK) is always False; rely on isfile.
    # conan2 cache dir is `gnupla03c6b9f7091e` → match `gnu*`.
    for p in sorted(
        glob.glob(os.path.join(home, ".conan2", "p", "gnu*", "p", "bin", "gnuplot"))
    ):
        if os.path.isfile(p):
            return p
    return None


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def main():
    if len(sys.argv) < 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    if not os.path.isdir(pkg):
        print("ERROR: package folder not found: %s" % pkg, file=sys.stderr)
        return 2

    gnuplot_bin = find_gnuplot_bin()
    if not gnuplot_bin:
        print("ERROR: no gnuplot executable found (PATH or ohpcd cache)", file=sys.stderr)
        return 2

    workdir = tempfile.mkdtemp(prefix="gplotpp-ohos-")
    bin_path = os.path.join(workdir, "ohos_consumer")
    cxx_src = os.path.join(workdir, "ohos_consumer.cpp")
    with open(cxx_src, "w") as f:
        f.write(TEST_CXX)

    env = os.environ.copy()
    env["PATH"] = os.path.dirname(gnuplot_bin) + os.pathsep + env.get("PATH", "")

    # T4: compile the consumer against the installed public header
    include_dir = os.path.join(pkg, "include")
    if not os.path.isdir(include_dir):
        print("ERROR: package include dir missing: %s" % include_dir, file=sys.stderr)
        return 2
    compile_run = run(
        [
            CXX,
            "-std=c++17",
            "-O2",
            "-g0",
            # Map the host home prefix out of debug/line info so the
            # consumer binary carries no absolute host paths (T3).
            "-ffile-prefix-map=%s=HOME/" % os.path.expanduser("~").rstrip("/"),
            "-o",
            bin_path,
            cxx_src,
            "-I",
            include_dir,
        ],
        env=env,
    )
    if compile_run.returncode != 0:
        print("ERROR: T4 consumer compile failed:", file=sys.stderr)
        print(compile_run.stderr.decode("utf-8", "replace"), file=sys.stderr)
        return 1

    checks = []

    # T1: ELF64 AArch64
    r = run([READELF, "-h", bin_path])
    if r.returncode != 0:
        print("ERROR: T1 readelf -h failed", file=sys.stderr)
        return 1
    head = r.stdout.decode("utf-8", "replace")
    checks.append(("T1_aarch64_elf", "ELF64" in head and "AArch64" in head,
                   "ELF64 AArch64 header"))

    # T2: musl, no GLIBC, no ld-linux
    r = run([STRINGS, bin_path])
    if r.returncode != 0:
        print("ERROR: T2 strings failed", file=sys.stderr)
        return 1
    strings_out = r.stdout
    has_glibc = b"GLIBC_" in strings_out
    has_ldlinux = b"ld-linux" in strings_out
    has_musl = b"musl" in strings_out
    checks.append(("T2_musl_no_glibc",
                   (not has_glibc) and (not has_ldlinux) and has_musl,
                   "musl libc, no GLIBC symbol versions, no ld-linux"))

    # T3: no host absolute paths, no RPATH/RUNPATH
    # NOTE: readelf -d must succeed before judging. A non-zero exit code
    # means the tool failed (missing/unexecutable/format error) and an empty
    # stdout must NOT be silently treated as "no RPATH/RUNPATH" — that would
    # be a false PASS. Fail loudly like T1/T2 instead.
    r = run([READELF, "-d", bin_path])
    if r.returncode != 0:
        print("ERROR: T3 readelf -d failed", file=sys.stderr)
        print(r.stderr.decode("utf-8", "replace"), file=sys.stderr)
        return 1
    readelf_d = r.stdout
    has_rpath = b"RPATH" in readelf_d or b"RUNPATH" in readelf_d
    host_hits = []
    for pat in HOST_PATH_RES:
        if pat in strings_out:
            host_hits.append(pat.decode("utf-8", "replace"))
    checks.append(("T3_no_host_paths",
                   (not host_hits) and (not has_rpath),
                   "no absolute host paths, no RPATH/RUNPATH (hits=%s)" % host_hits))

    # T4: real plotting through the installed header (run + label verify)
    r = run([bin_path], env=env, cwd=workdir)
    checks.append(("T4_real_plot", r.returncode == 0,
                   "consumer exit code %d" % r.returncode))

    failed = 0
    for cid, ok, note in checks:
        print("  %s %s — %s" % ("PASS" if ok else "FAIL", cid, note))
        if not ok:
            failed += 1
    if failed:
        print("ERROR: %d of %d test_ohos checks failed" % (failed, len(checks)),
              file=sys.stderr)
        return 1
    print("ALL test_ohos CHECKS PASSED (%d)" % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
