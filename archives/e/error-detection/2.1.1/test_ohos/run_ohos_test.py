#!/usr/bin/env python3
"""test_ohos — error-detection 2.1.1 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实校验计算（checkSum8/16/32 + CRC-8/16/32 标准校验向量，链最终静态库，非伪造输出）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
CC = os.environ.get("CC", "clang")
STRINGS = os.environ.get("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"error-detection-2.1.1"]

TEST_C = r"""
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include "err.h"

/* "123456789" 标准测试向量 */
static const uint8_t tv[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};

int main(void)
{
    /* T5a: 累加校验和（'1'..'9' = 0x31..0x39 => sum = 477 = 0x1DD） */
    if (checkSum8_Calc((uint8_t *)tv, sizeof(tv)) != 0xDD) return 1;
    if (checkSum16_Calc((uint8_t *)tv, sizeof(tv)) != 0x01DD) return 2;
    if (checkSum32_Calc((uint8_t *)tv, sizeof(tv)) != 0x000001DDu) return 3;

    /* T5b: CRC-8/MAXIM = 0xA1 */
    hcrc8_T crc8 = {.Poly = 0x31, .Init = 0x00, .refIn = true, .refOut = true, .xorOut = 0x00};
    if (CRC8_Calc(&crc8, (uint8_t *)tv, sizeof(tv)) != 0xA1) return 4;

    /* T5c: CRC-16/CCITT-FALSE = 0x29B1 */
    hcrc16_T crc16 = {.Poly = 0x1021, .Init = 0xFFFF, .refIn = false, .refOut = false, .xorOut = 0x0000};
    if (CRC16_Calc(&crc16, (uint8_t *)tv, sizeof(tv)) != 0x29B1) return 5;

    /* T5d: CRC-32/IEEE = 0xCBF43926 */
    hcrc32_T crc32 = {.Poly = 0x04C11DB7, .Init = 0xFFFFFFFF, .refIn = true, .refOut = true, .xorOut = 0xFFFFFFFF};
    if (CRC32_Calc(&crc32, (uint8_t *)tv, sizeof(tv)) != 0xCBF43926u) return 6;

    printf("OHOS_ERRDET_TESTS_PASS: sum8=0xDD sum16=0x01DD crc8=0xA1 crc16=0x29B1 crc32=0xCBF43926\n");
    return 0;
}
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")

    work = tempfile.mkdtemp(prefix="errdet-test-ohos-")
    src = os.path.join(work, "test_ohos.c")
    with open(src, "w") as f:
        f.write(TEST_C)
    exe = os.path.join(work, "test_ohos")

    # 编译 + 链接最终包（公开头文件 + 正常链接目标）
    comp = subprocess.run(
        [CC, "-O2", "-I", include, src, "-L", lib, "-lerror-detection",
         "-o", exe],
        capture_output=True, text=True)
    if comp.returncode != 0:
        print("FAIL: compile/link failed:\n" + comp.stderr, file=sys.stderr)
        return 1

    # T1: ELF64 AArch64
    r = subprocess.run([READELF, "-h", exe], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: not ELF64 AArch64", file=sys.stderr)
        return 1

    # T2: musl libc（NEEDED 中无 glibc / ld-linux）
    r = subprocess.run([READELF, "-d", exe], capture_output=True)
    if b"GLIBC" in r.stdout or b"ld-linux" in r.stdout:
        print("FAIL: glibc/ld-linux detected", file=sys.stderr)
        return 1

    # T3: .codesign 段存在（OHOS 签名管线产出）
    r = subprocess.run([READELF, "-S", exe], capture_output=True)
    if b".codesign" not in r.stdout:
        print("FAIL: .codesign section missing", file=sys.stderr)
        return 1

    # T4: 无宿主机绝对路径 + 无 RPATH/RUNPATH
    st = subprocess.run([STRINGS, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1
    r = subprocess.run([READELF, "-d", exe], capture_output=True)
    if b"RPATH" in r.stdout or b"RUNPATH" in r.stdout:
        print("FAIL: RPATH/RUNPATH present", file=sys.stderr)
        return 1

    # T5: 真实运行（链最终静态库，真实校验计算）
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print("FAIL: test run failed rc=%d:\n%s%s" % (run.returncode, run.stdout, run.stderr), file=sys.stderr)
        return 1
    print(run.stdout, end="")
    if "OHOS_ERRDET_TESTS_PASS" not in run.stdout:
        print("FAIL: test did not report PASS", file=sys.stderr)
        return 1

    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
