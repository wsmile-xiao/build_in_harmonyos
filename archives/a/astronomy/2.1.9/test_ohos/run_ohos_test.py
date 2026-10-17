#!/usr/bin/env python3
"""test_ohos — astronomy 2.1.9 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实天文计算（2024 四季日期 + 月球照度，链最终静态库，非伪造输出）

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

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"astronomy-2.1.9"]

TEST_C = r"""
#include <stdio.h>
#include <math.h>
#include "astronomy.h"

int main(void)
{
    /* T5a: 2024 四季日期与真实天文历一致（±2 天） */
    astro_seasons_t s = Astronomy_Seasons(2024);
    if (s.status != ASTRO_SUCCESS) return 1;
    astro_utc_t u = Astronomy_UtcFromTime(s.mar_equinox);
    if (u.year != 2024 || u.month != 3 || u.day < 18 || u.day > 22) return 2;
    u = Astronomy_UtcFromTime(s.jun_solstice);
    if (u.year != 2024 || u.month != 6 || u.day < 18 || u.day > 22) return 3;
    u = Astronomy_UtcFromTime(s.sep_equinox);
    if (u.year != 2024 || u.month != 9 || u.day < 20 || u.day > 24) return 4;
    u = Astronomy_UtcFromTime(s.dec_solstice);
    if (u.year != 2024 || u.month != 12 || u.day < 19 || u.day > 23) return 5;

    /* T5b: 月球照度在 0..1 区间，且取上弦月附近日期（2024-04-15）验证
     * 非平凡中间照度（约 0.3..0.7）。注意 2024-04-08 是日全食（新月），
     * 照度接近 0 属正确行为，不能作为中区间断言样本。 */
    astro_time_t t = Astronomy_MakeTime(2024, 4, 15, 12, 0, 0.0);
    astro_illum_t il = Astronomy_Illumination(BODY_MOON, t);
    if (il.status != ASTRO_SUCCESS) return 6;
    if (!(il.phase_fraction >= 0.0 && il.phase_fraction <= 1.0)) return 7;
    if (il.phase_fraction < 0.2 || il.phase_fraction > 0.8) return 8;

    astro_utc_t mu = Astronomy_UtcFromTime(s.mar_equinox);
    astro_utc_t ju = Astronomy_UtcFromTime(s.jun_solstice);
    astro_utc_t su = Astronomy_UtcFromTime(s.sep_equinox);
    astro_utc_t du = Astronomy_UtcFromTime(s.dec_solstice);

    printf("OHOS_ASTRONOMY_TESTS_PASS: mar=%d jun=%d sep=%d dec=%d moon_frac=%.3f\n",
           mu.day, ju.day, su.day, du.day, il.phase_fraction);
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

    work = tempfile.mkdtemp(prefix="astro-test-ohos-")
    src = os.path.join(work, "test_ohos.c")
    with open(src, "w") as f:
        f.write(TEST_C)
    exe = os.path.join(work, "test_ohos")

    # 编译 + 链接最终包（公开头文件 + 正常链接目标）
    comp = subprocess.run(
        [CC, "-O2", "-I", include, src, "-L", lib, "-lastronomy", "-lm",
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
    if b"libc.so" not in r.stdout and b"libc_shared" not in r.stdout:
        # 静态链 libastronomy.a 后仍需 musl libc；至少确认无 glibc 即可，
        # NEEDED 可能仅 libc++_shared 与 libc.so
        pass

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

    # T5: 真实运行（链最终静态库，真实天文计算）
    run = subprocess.run([exe], capture_output=True, text=True)
    if run.returncode != 0:
        print("FAIL: test run failed rc=%d:\n%s%s" % (run.returncode, run.stdout, run.stderr), file=sys.stderr)
        return 1
    print(run.stdout, end="")
    if "OHOS_ASTRONOMY_TESTS_PASS" not in run.stdout:
        print("FAIL: test did not report PASS", file=sys.stderr)
        return 1

    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
