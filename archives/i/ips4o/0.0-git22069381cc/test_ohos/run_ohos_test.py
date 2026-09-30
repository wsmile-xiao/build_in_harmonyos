#!/usr/bin/env python3
"""test_ohos — ips4o 0.0-git22069381cc HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, clang 15）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64，非 x86）
  T2  真实并行排序：ips4o::parallel::sort 对 4M 随机 uint64 排序，
      与 std::sort 参考结果逐元素比对（非伪造输出）
  T3  顺序排序 + 自定义比较器（降序）验证公开 API 泛型形态
  T4  无宿主绝对路径泄漏（RPATH/RUNPATH/字符串检查）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF") or shutil.which("readelf") or "/data/service/hnp/bin/llvm-readelf"
CC = os.environ.get("CC") or shutil.which("clang") or "/data/service/hnp/bin/clang"
STRINGS = os.environ.get("STRINGS") or shutil.which("strings") or "/data/service/hnp/bin/llvm-strings"
# OHOS SDK llvm/lib：libc++/libc++abi/libomp 所在（clang 驱动默认搜索路径不含，
# 需显式 -L 传入，否则链接报 undefined std::logic_error 等 libc++ 运行时符号）
OHOS_LLVM_LIB = os.environ.get(
    "OHOS_LLVM_LIB",
    "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
)

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"ips4o-0.0-git22069381cc"]

TEST_CPP = r"""
#include <ips4o.hpp>
#include <vector>
#include <cstdint>
#include <cstdio>
#include <algorithm>
#include <cstdlib>

static uint64_t rnd64(uint64_t& s) {
    s ^= s << 13; s ^= s >> 7; s ^= s << 17;
    return s;
}

int main() {
    constexpr size_t N = 4u << 20;   // 4M
    uint64_t seed = 0x9E3779B97F4A7C15ull;

    // T2: 并行排序 vs std::sort 参考
    std::vector<uint64_t> a(N), b(N);
    for (size_t i = 0; i < N; ++i) { a[i] = rnd64(seed); b[i] = a[i]; }
    ips4o::parallel::sort(a.begin(), a.end());
    std::sort(b.begin(), b.end());
    if (!std::equal(a.begin(), a.end(), b.begin())) {
        std::printf("OHOS_T2_PARALLEL_FAIL\n");
        return 2;
    }

    // T3: 顺序排序 + 降序比较器
    std::vector<int64_t> c(1u << 20), d(1u << 20);
    for (size_t i = 0; i < c.size(); ++i) c[i] = static_cast<int64_t>((i * 7919u) % 1000003u) - 500000;
    d = c;
    ips4o::sort(c.begin(), c.end(), [](int64_t x, int64_t y) { return x > y; });
    std::sort(d.begin(), d.end(), [](int64_t x, int64_t y) { return x > y; });
    if (!std::equal(c.begin(), c.end(), d.begin())) {
        std::printf("OHOS_T3_COMPARATOR_FAIL\n");
        return 3;
    }

    std::printf("OHOS_IPS4O_TESTS_PASS parallel=4M comparator=1M\n");
    return 0;
}
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")

    work = tempfile.mkdtemp(prefix="ips4o-test-ohos-")
    src = os.path.join(work, "test_ohos.cpp")
    with open(src, "w") as f:
        f.write(TEST_CPP)
    exe = os.path.join(work, "test_ohos")

    # 编译：并行路径需要 OpenMP（thread_pool.hpp 无条件包含 <omp.h>）；
    # OHOS 链接需显式 -stdlib=libc++ 与 -lc++ -lc++abi（SDK 运行时符号），
    # 并给出 SDK libc++/libomp 搜索路径，否则报 undefined std::logic_error 等。
    cc_cmd = [CC, "-std=c++14", "-O2", "-stdlib=libc++", "-fopenmp", "-pthread",
              "-I", include, "-L", OHOS_LLVM_LIB, "-lc++", "-lc++abi",
              src, "-o", exe]
    cc = subprocess.run(cc_cmd, capture_output=True, text=True)
    if cc.returncode != 0:
        print("COMPILE_FAILED\n" + cc.stderr[-2000:], file=sys.stderr)
        return 1

    # T1: aarch64 ELF 验证
    re_elf = subprocess.run([READELF, "-h", exe], capture_output=True, text=True)
    if re_elf.returncode != 0 or "AArch64" not in re_elf.stdout:
        print("T1_FAIL: consumer executable is not ELF64 AArch64", file=sys.stderr)
        return 1

    # T4: 无宿主绝对路径泄漏
    st = subprocess.run([STRINGS, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print(f"T4_FAIL: host path leak {pat!r}", file=sys.stderr)
            return 1

    # T2/T3: 真实运行
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print(f"RUN_FAILED rc={run.returncode}\n{run.stdout}\n{run.stderr}", file=sys.stderr)
        return 1
    if "OHOS_IPS4O_TESTS_PASS" not in run.stdout:
        print("RUN_FAILED: missing pass marker\n" + run.stdout, file=sys.stderr)
        return 1
    print(run.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())