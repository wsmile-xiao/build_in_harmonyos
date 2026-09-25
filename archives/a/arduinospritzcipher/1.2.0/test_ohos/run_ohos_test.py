#!/usr/bin/env python3
"""test_ohos — arduinospritzcipher 1.2.0 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实密码学验证（Spritz 论文 RS14 测试向量：hash('ABC') 256-bit、
      crypt 加解密 roundtrip、mac 确定性、PRNG 种子确定性；链最终静态库）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF", "readelf")
CC = os.environ.get("CC", "clang")
STRINGS = os.environ.get("STRINGS", "strings")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"ArduinoSpritzCipher-1.2.0"]

TEST_C = r"""
#include <stdio.h>
#include <stdint.h>
#include "SpritzCipher.h"

/* Spritz 论文 RS14 (Page 30) 官方测试向量：hash('ABC') 256-bit */
static const uint8_t expect_hash_abc[32] = {
    0x02, 0x8f, 0xa2, 0xb4, 0x8b, 0x93, 0x4a, 0x18,
    0x62, 0xb8, 0x69, 0x10, 0x51, 0x3a, 0x47, 0x67,
    0x7c, 0x1c, 0x2d, 0x95, 0xec, 0x3e, 0x75, 0x70,
    0x78, 0x6f, 0x1c, 0x32, 0x8b, 0xbd, 0x4a, 0x47
};

static int nfail = 0;

static int t_hash(void)
{
    uint8_t digest[32];
    spritz_hash(digest, sizeof(digest), (const uint8_t *)"ABC", 3);
    return spritz_compare(digest, expect_hash_abc, 32) == 0 ? 0 : 1;
}

static int t_crypt_roundtrip(void)
{
    const uint8_t msg[3] = {'A', 'B', 'C'};
    const uint8_t key[3] = {0x00, 0x01, 0x02};
    uint8_t buf[8], dec[8];
    spritz_ctx ctx;
    spritz_setup(&ctx, key, sizeof(key));
    spritz_crypt(&ctx, msg, sizeof(msg), buf);
    spritz_setup(&ctx, key, sizeof(key));
    spritz_crypt(&ctx, buf, sizeof(msg), dec);
    return spritz_compare(dec, msg, sizeof(msg)) == 0 ? 0 : 1;
}

static int t_crypt_inplace(void)
{
    const uint8_t msg[3] = {'A', 'B', 'C'};
    const uint8_t key[3] = {0x00, 0x01, 0x02};
    uint8_t buf[3];
    spritz_ctx ctx;
    buf[0] = msg[0]; buf[1] = msg[1]; buf[2] = msg[2];
    spritz_setup(&ctx, key, sizeof(key));
    spritz_crypt_inplace(&ctx, buf, sizeof(buf));
    spritz_setup(&ctx, key, sizeof(key));
    spritz_crypt_inplace(&ctx, buf, sizeof(buf));
    return spritz_compare(buf, msg, sizeof(msg)) == 0 ? 0 : 1;
}

static int t_mac_deterministic(void)
{
    const uint8_t msg[3] = {'A', 'B', 'C'};
    const uint8_t key[3] = {0x00, 0x01, 0x02};
    uint8_t mac1[16], mac2[16];
    spritz_mac(mac1, sizeof(mac1), msg, sizeof(msg), key, sizeof(key));
    spritz_mac(mac2, sizeof(mac2), msg, sizeof(msg), key, sizeof(key));
    return spritz_compare(mac1, mac2, sizeof(mac1)) == 0 ? 0 : 1;
}

static int t_prng_deterministic(void)
{
    uint8_t a[64], b[64];
    spritz_ctx ctx;
    uint8_t seed[16] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
    unsigned int i;
    spritz_setup(&ctx, seed, sizeof(seed));
    for (i = 0; i < sizeof(a); i++) a[i] = spritz_random8(&ctx);
    spritz_setup(&ctx, seed, sizeof(seed));
    for (i = 0; i < sizeof(b); i++) b[i] = spritz_random8(&ctx);
    return spritz_compare(a, b, sizeof(a)) == 0 ? 0 : 1;
}

int main(void)
{
    printf("OHOS_SPRITZ: version=%s\n", SPRITZ_LIBRARY_VERSION_STRING);
    if (t_hash()) { printf("T5-hash FAIL\n"); nfail++; }
    if (t_crypt_roundtrip()) { printf("T5-crypt FAIL\n"); nfail++; }
    if (t_crypt_inplace()) { printf("T5-crypt_inplace FAIL\n"); nfail++; }
    if (t_mac_deterministic()) { printf("T5-mac FAIL\n"); nfail++; }
    if (t_prng_deterministic()) { printf("T5-prng FAIL\n"); nfail++; }
    if (nfail == 0) {
        printf("OHOS_SPRITZ_TESTS_PASS\n");
        return 0;
    }
    printf("OHOS_SPRITZ_FAILURES=%d\n", nfail);
    return 1;
}
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    include = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")

    work = tempfile.mkdtemp(prefix="spritz-test-ohos-")
    src = os.path.join(work, "test_ohos.c")
    with open(src, "w") as f:
        f.write(TEST_C)
    exe = os.path.join(work, "test_ohos")

    # 编译 + 链接最终包（公开头文件 + 正常链接目标）
    comp = subprocess.run(
        [CC, "-O2", "-I", include, src, "-L", lib, "-lSpritzCipher",
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

    # T4: 无宿主机绝对路径
    st = subprocess.run([STRINGS, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1

    # T5: 真实运行（链最终静态库，真实密码学计算）
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print("FAIL: test run failed rc=%d:\n%s%s" % (run.returncode, run.stdout, run.stderr), file=sys.stderr)
        return 1
    print(run.stdout, end="")
    if "OHOS_SPRITZ_TESTS_PASS" not in run.stdout:
        print("FAIL: test did not report PASS", file=sys.stderr)
        return 1

    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
