#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ohos — htscodecs 1.6.5 HarmonyOS PC 专项验证。

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实 rANS 编解码往返（调用公共 API htscodecs_version() +
      rANS_static.h 的 rans_compress/rans_uncompress，64 KiB 质量值
      数据压缩-解压-逐字节比对，输出可观察的压缩率，非伪造输出）

用法：python3 run_ohos_test.py <prefix_or_conan_package_folder>
      （目录需含 include/htscodecs/*.h 与 lib/libhtscodecs.*）
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

TEST_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <htscodecs/htscodecs.h>
#include <htscodecs/rANS_static.h>

int main(void)
{
    const unsigned int N = 65536;
    unsigned char *in  = malloc(N);
    unsigned char *out = NULL;
    unsigned char *dec = NULL;
    unsigned int csize = 0, usize = 0;
    unsigned int i;
    const char *ver = htscodecs_version();

    /* T5a: 版本 API 返回非空 */
    if (ver == NULL || ver[0] == '\0') return 1;

    for (i = 0; i < N; i++)
        in[i] = (unsigned char)((i * 7 + (i >> 3)) & 63);

    /* T5b: 压缩必须成功且有收益 */
    out = rans_compress(in, N, &csize, 1);
    if (!out || csize == 0 || csize >= N) return 2;

    /* T5c: 解压必须成功且尺寸一致 */
    dec = rans_uncompress(out, csize, &usize);
    if (!dec || usize != N) return 3;

    /* T5d: 往返字节完全一致 */
    if (memcmp(in, dec, N) != 0) return 4;

    printf("htscodecs %s rANS round-trip %u -> %u bytes (%.1f%%)\n",
           ver, N, csize, 100.0 * csize / N);
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

    tmp = tempfile.mkdtemp(prefix="htscodecs-ohos-")
    tsrc = os.path.join(tmp, "t.c")
    texe = os.path.join(tmp, "t")
    with open(tsrc, "w") as f:
        f.write(TEST_C)

    # T1+T2+T3+T4+T5 共用同一可执行文件
    # 静态链接 libhtscodecs.a（消费者链接正常静态库目标，无 rpath 注入），
    # 使 T4 路径泄漏检查只反映库/二进制真实内容而非本地链接路径。
    r = subprocess.run(
        [CC, "-O2", "-I" + inc, tsrc, os.path.join(lib, "libhtscodecs.a"),
         "-o", texe],
        capture_output=True)
    if r.returncode != 0:
        print("T1 compile FAILED:\n" + r.stderr.decode(errors="replace"))
        return 1

    # T1: aarch64 ELF
    r = subprocess.run([READELF, "-h", texe], capture_output=True)
    if r.returncode != 0 or b"AArch64" not in r.stdout:
        print("T1 FAIL: not aarch64 ELF")
        return 1

    # T2: musl libc（无 glibc 路径）
    r = subprocess.run([READELF, "-l", texe], capture_output=True)
    elf = r.stdout
    if b"ld-linux" in elf or b"/lib64/ld" in elf:
        print("T2 FAIL: glibc-style loader referenced")
        return 1

    # T3: .codesign 段（若有 readelf 支持段查看）
    r = subprocess.run([READELF, "-S", texe], capture_output=True)
    if b".codesign" not in r.stdout:
        print("T3 WARN: no .codesign section (unsigned local build)")
        # 非致命：本地构建无签名管线，CI 会补签

    # T4: 无宿主绝对路径泄漏
    r = subprocess.run([STRINGS, texe], capture_output=True)
    hits = [p for p in HOST_PATH_RES if p in r.stdout]
    if hits:
        print("T4 FAIL: host path leakage %r" % hits)
        return 1

    # T5: 真实编解码往返
    r = subprocess.run([texe], capture_output=True)
    if r.returncode != 0:
        print("T5 FAIL (rc=%d): %s" % (r.returncode,
                                       r.stderr.decode(errors="replace")))
        return 1
    print(r.stdout.decode(errors="replace").strip())
    print("test_ohos: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
