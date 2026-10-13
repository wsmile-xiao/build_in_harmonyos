#!/usr/bin/env python3
"""test_ohos — google-sparsehash 2.0.4 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（OHOS aarch64）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  legacy google/ include 树：default 值类型容器的插入/删除
  T2  sparsehash/ include 树 + std::string key（std::hash）
  T3  5000 元素增长跨 sparse group（DEFAULT_GROUP_SIZE=48）+ churn
  T4  dense 容器 2000 插入/半数删除触发 resize/rehash，负数哨兵 key
  T5  编译产物架构：aarch64 ELF64（readelf 校验）

google-sparsehash 是 header-only 库（无 ELF library 产物），因此本专项
不虚构 ELF library 检查，而是验证：OHOS 本机真实编译运行 + 产物架构 +
两条公开 include 树（sparsehash/ 与 google/）的真实可用性。

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import shutil
import subprocess
import sys
import tempfile

CXX = os.environ.get("CXX", "clang++")
READELF = os.environ.get("READELF", "readelf")

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_CPP = os.path.join(HERE, "ohos_special_test.cpp")


def resolve(name):
    """OHOS python3 subprocess 不按 PATH 解析裸命令（posix_spawn 不搜索
    PATH），统一用 shutil.which 解析为绝对路径。"""
    full = shutil.which(name)
    return name if full is None else full


def run(cmd, **kw):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    if len(sys.argv) < 2:
        print("usage: python3 run_ohos_test.py <conan_package_folder>")
        return 2
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    if not os.path.isdir(os.path.join(inc, "sparsehash")):
        print(f"[FAIL] package include tree not found under {inc}")
        return 1
    print(f"  [INFO] include dir: {inc}")

    with tempfile.TemporaryDirectory(prefix="ohos-test-gsh-") as td:
        exe = os.path.join(td, "ohos_special_test")

        # T1-T4: 通过包 include 路径编译（真实 OHOS 工具链），然后运行
        r = run([resolve(CXX), "-std=c++11", "-Wall", "-Wextra", "-O2",
                 f"-I{inc}", "-o", exe, TEST_CPP])
        if r.returncode != 0:
            print("[FAIL] compile ohos_special_test.cpp:")
            print(r.stderr[-2000:])
            return 1
        print("  [PASS] compile via package include (OHOS toolchain, c++11)")

        # T5: 产物架构校验（header-only 无 ELF library，只校验测试可执行档）
        r = run([resolve(READELF), "-h", exe])
        if r.returncode == 0 and "ELF64" in r.stdout and "AArch64" in r.stdout:
            print("  [PASS] binary is ELF64 AArch64")
        elif r.returncode == 0:
            print("[FAIL] binary is not ELF64 AArch64:")
            print(r.stdout[:400])
            return 1
        else:
            print("  [WARN] readelf unavailable; skipping architecture check")
            print("         ", (r.stderr or r.stdout)[:200].replace("\n", " "))

        r = run([exe])
        if r.returncode != 0:
            print(f"[FAIL] OHOS special test rc={r.returncode}")
            print(r.stdout)
            print(r.stderr)
            return 1
        print(" ", r.stdout.strip())
        if "ALL PASS" not in r.stdout:
            print("[FAIL] special test did not report ALL PASS")
            return 1

    print("test_ohos google-sparsehash: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
