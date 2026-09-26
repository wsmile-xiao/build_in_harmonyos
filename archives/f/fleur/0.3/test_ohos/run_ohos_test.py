#!/usr/bin/env python3
"""test_ohos — fleur 0.3 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实 Bloom Filter 计算（add/check + 序列化往返 + join，链最终静态库，非伪造输出）

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

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"fleur-0.3"]

TEST_C = r"""
#include <stdio.h>
#include <string.h>
#include "fleur.h"

int main(void)
{
    /* T5a: 创建容量 10000、误报率 0.001 的 filter，检查初始化参数一致性 */
    BloomFilter bf = fleur_initialize(10000, 0.001, "ohos");
    if (bf.h.version != 1) return 1;
    if (bf.h.n != 10000) return 2;
    if (bf.h.k == 0 || bf.h.m == 0) return 3;

    /* T5b: 加入一批条目并逐一验证命中 */
    const char *items[] = {
        "bloom", "filter", "harmonyos", "aarch64", "musl",
        "ohos-pc", "fnv-hash", "false-positive", "serialize", "join"
    };
    for (int i = 0; i < 10; i++) {
        if (fleur_add(&bf, (char*)items[i], strlen(items[i])) != 1) return 4;
    }
    for (int i = 0; i < 10; i++) {
        if (fleur_check(&bf, (char*)items[i], strlen(items[i])) != 1) return 5;
    }
    /* T5c: 未加入条目不应命中（低误报率配置下确定性足够） */
    const char *absent = "definitely-not-in-filter-xyz";
    if (fleur_check(&bf, (char*)absent, strlen(absent)) != 0) return 6;

    /* T5d: 序列化往返：写入文件 -> 重新加载 -> 仍可命中全部条目 */
    const char *path = "./fleur-ohos-roundtrip.bloom";
    FILE *f = fopen(path, "wb");
    if (!f) return 7;
    if (fleur_bloom_filter_to_file(&bf, f) != 1) return 8;
    fclose(f);

    f = fopen(path, "rb");
    if (!f) return 9;
    BloomFilter bf2 = fleur_bloom_filter_from_file(f);
    fclose(f);
    if (bf2.error != 0) return 10;
    for (int i = 0; i < 10; i++) {
        if (fleur_check(&bf2, (char*)items[i], strlen(items[i])) != 1) return 11;
    }

    /* T5e: join 两个兼容 filter */
    BloomFilter dst = fleur_initialize(10000, 0.001, "dst");
    if (fleur_join(&bf2, &dst) != 1) return 12;

    fleur_destroy_filter(&bf);
    fleur_destroy_filter(&bf2);
    fleur_destroy_filter(&dst);
    remove(path);

    printf("OHOS_FLEUR_TESTS_PASS: k=%llu m=%llu n=%llu\n",
           (unsigned long long)bf.h.k, (unsigned long long)bf.h.m,
           (unsigned long long)bf.h.n);
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

    work = tempfile.mkdtemp(prefix="fleur-test-ohos-")
    src = os.path.join(work, "test_ohos.c")
    with open(src, "w") as f:
        f.write(TEST_C)
    exe = os.path.join(work, "test_ohos")

    # 编译 + 链接最终包（公开头文件 + 正常链接目标）
    comp = subprocess.run(
        [CC, "-O2", "-I", include, src, "-L", lib, "-lfleur", "-lfnv",
         "-lmyutils", "-lm", "-o", exe],
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

    # T5: 真实运行（链最终静态库，真实 bloom 计算）
    run = subprocess.run([exe], capture_output=True, text=True, cwd=work)
    if run.returncode != 0:
        print("FAIL: test run failed rc=%d:\n%s%s" % (run.returncode, run.stdout, run.stderr), file=sys.stderr)
        return 1
    print(run.stdout, end="")
    if "OHOS_FLEUR_TESTS_PASS" not in run.stdout:
        print("FAIL: test did not report PASS", file=sys.stderr)
        return 1

    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
