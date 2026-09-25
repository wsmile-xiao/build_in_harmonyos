#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ohos-htscodecs-consumer — htscodecs 1.6.5 消费者用例（R34/R51 硬门禁）

模拟业务上层组件（如"测序数据压缩中间件"）使用 htscodecs 的最终
Conan 包：仅通过已安装/导出的公开头文件（htscodecs/htscodecs.h、
htscodecs/rANS_static.h）、公开 API、正常链接目标（-lhtscodecs）
与静态库运行时产物消费该三方库，验证第三方使用者能否编译、链接、
调用并正常运行。

检查项（任一失败必须非零退出）：
  A. 最终包内静态库/消费者可执行文件为 ELF64 AArch64
  B. 消费者程序使用公开 API（htscodecs_version() / rans_compress /
     rans_uncompress）并产生可观察结果
  C. 压缩-解压往返后数据逐字节一致（业务语义：质量值流无损还原）
  D. 压缩确有收益（输出压缩率 > 0 且 < 100%，业务上压缩中间件可依赖）
  E. 二进制不含宿主机绝对路径（/storage/、/home/、/Users/）

用法：python3 run_ohos_test.py <prefix_or_conan_package_folder>
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

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"htscodecs-1.6.5"]

CONSUMER_C = r"""
/* 消费者：测序数据压缩中间件——把一批质量值记录无损压缩归档。 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <htscodecs/htscodecs.h>
#include <htscodecs/rANS_static.h>

int main(void)
{
    const unsigned int N = 131072;
    unsigned char *reads = malloc(N);       /* 模拟 128 KiB 质量值流 */
    unsigned char *arch  = NULL;
    unsigned char *restored = NULL;
    unsigned int arch_sz = 0, restored_sz = 0;
    unsigned int i;
    const char *ver = htscodecs_version();

    if (ver == NULL || ver[0] == '\0') {
        fprintf(stderr, "consumer FAIL: version API unusable\n");
        return 1;
    }
    /* 有偏质量值分布（测序质量值集中在 Q20-Q40），压缩应显著。 */
    for (i = 0; i < N; i++)
        reads[i] = (unsigned char)(30 + ((i * 13 + (i >> 4)) & 7));

    arch = rans_compress(reads, N, &arch_sz, 1);
    if (!arch || arch_sz == 0 || arch_sz >= N) {
        fprintf(stderr, "consumer FAIL: compress rc=0 arch_sz=%u\n", arch_sz);
        return 2;
    }

    restored = rans_uncompress(arch, arch_sz, &restored_sz);
    if (!restored || restored_sz != N) {
        fprintf(stderr, "consumer FAIL: uncompress rc=0 sz=%u want=%u\n",
                restored_sz, N);
        return 3;
    }
    if (memcmp(reads, restored, N) != 0) {
        fprintf(stderr, "consumer FAIL: round-trip mismatch\n");
        return 4;
    }

    printf("consumer OK: htscodecs %s archived %u quality bytes to %u "
           "(%.2f%% size), restored losslessly\n",
           ver, N, arch_sz, 100.0 * arch_sz / N);
    return 0;
}
"""


def main():
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <prefix_or_conan_package_folder>")
        return 2
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")
    if not (os.path.isdir(os.path.join(inc, "htscodecs")) and os.path.isdir(lib)):
        print("ERROR: %s lacks include/htscodecs or lib/" % pkg)
        return 2

    tmp = tempfile.mkdtemp(prefix="htscodecs-consumer-")
    csrc = os.path.join(tmp, "consumer.c")
    cexe = os.path.join(tmp, "consumer")
    with open(csrc, "w") as f:
        f.write(CONSUMER_C)

    r = subprocess.run(
        [CC, "-O2", "-I" + inc, csrc, os.path.join(lib, "libhtscodecs.a"),
         "-o", cexe],
        capture_output=True)
    if r.returncode != 0:
        print("compile FAILED:\n" + r.stderr.decode(errors="replace"))
        return 1

    # A: aarch64 ELF
    r = subprocess.run([READELF, "-h", cexe], capture_output=True)
    if r.returncode != 0 or b"AArch64" not in r.stdout:
        print("A FAIL: not aarch64 ELF")
        return 1

    # E: 无宿主路径泄漏
    r = subprocess.run([STRINGS, cexe], capture_output=True)
    hits = [p for p in HOST_PATH_RES if p in r.stdout]
    if hits:
        print("E FAIL: host path leakage %r" % hits)
        return 1

    # B/C/D: 运行消费者，检查可观察结果
    r = subprocess.run([cexe], capture_output=True)
    if r.returncode != 0:
        print("consumer run FAIL (rc=%d): %s" % (r.returncode,
                                                 r.stderr.decode(errors="replace")))
        return 1
    print(r.stdout.decode(errors="replace").strip())
    print("ohos-htscodecs-consumer: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
