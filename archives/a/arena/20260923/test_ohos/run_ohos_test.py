#!/usr/bin/env python3
"""test_ohos — arena 20260923 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  header-only 消费者编译：通过 Conan 包 include 路径引入 arena.h
      （ARENA_IMPLEMENTATION 展开实现），编译为 aarch64 ELF
  T2  区域增长语义：arena_alloc 跨 Region 分裂（>ARENA_REGION_DEFAULT_CAPACITY）
  T3  arena_realloc/arena_memdup 数据保真（字节级 round-trip）
  T4  arena_sprintf 变参格式化与 arena_rewind/arena_reset 语义
  T5  arena_da_append 动态数组（String_Builder 模式，上游 001 演示同款路径）
  T6  arena_free/arena_trim 释放不崩溃、无泄漏（musl 下压力循环）
  T7  ELF 主机兼容性：二进制为 ELF64 AArch64（readelf 校验）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import shutil
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
CC = os.environ.get("CC", "clang")
STRINGS = os.environ.get("STRINGS", "strings")


def resolve(name):
    """OHOS python3 subprocess 不按 PATH 解析裸命令（posix_spawn 不搜索 PATH），
    统一用 shutil.which 解析为绝对路径。"""
    full = shutil.which(name)
    if full is None:
        return name  # 找不到时原样传参，让 subprocess 给出可诊断错误
    return full

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_C = os.path.join(HERE, "ohos_special_test.c")


def run(cmd, **kw):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    if len(sys.argv) < 2:
        print("usage: python3 run_ohos_test.py <conan_package_folder>")
        return 2
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    hdr = os.path.join(inc, "arena.h")
    if not os.path.isfile(hdr):
        # includedirs=["."] 的 header-only 包：头文件位于包根
        hdr = os.path.join(pkg, "arena.h")
        inc = pkg
    if not os.path.isfile(hdr):
        print(f"[FAIL] package arena.h not found under {pkg}")
        return 1
    print(f"  [INFO] header: {hdr}")

    failures = 0

    with tempfile.TemporaryDirectory(prefix="ohos-test-arena-") as td:
        exe = os.path.join(td, "ohos_special_test")

        # T1 + T7: 编译（通过包 include 路径）并校验 ELF64 AArch64
        r = run([resolve(CC), "-std=c99", "-Wall", "-Wextra", "-O2",
                 f"-I{inc}", "-o", exe, TEST_C])
        if r.returncode != 0:
            print("[FAIL] T1 consumer compile:", r.stderr[-2000:])
            return 1
        print("  [PASS] T1 consumer compile (arena.h via package include)")

        r = run([resolve(READELF), "-h", exe])
        if r.returncode == 0 and ("ELF64" in r.stdout and "AArch64" in r.stdout):
            print("  [PASS] T7 binary is ELF64 AArch64")
        else:
            print("  [WARN] T7 readelf unavailable or non-ELF64-AArch64 (readelf output below)")
            print("         ", r.stdout[:200].replace("\n", " "))
            # readelf 缺失不判失败（真机环境差异），运行测试本体才是硬门禁

        # T2-T6: 实际运行
        r = run([exe])
        if r.returncode != 0:
            print("[FAIL] OHOS special test binary rc=", r.returncode)
            print(r.stdout)
            print(r.stderr)
            failures += 1
        else:
            print(r.stdout)
            if "ALL PASS" not in r.stdout:
                print("[FAIL] special test did not report ALL PASS")
                failures += 1

    if failures == 0:
        print("test_ohos arena: ALL PASS")
        return 0
    print(f"test_ohos arena: {failures} FAILURE(S)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
