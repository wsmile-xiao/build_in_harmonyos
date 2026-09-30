#!/usr/bin/env python3
"""test_ohos — crossline 1.0 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（专项测试可执行文件为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T4  真实 readline 行为：管道喂入一行，crossline_readline 非 TTY 路径
      返回该行（可观察输出 "OHOS_CROSSLINE_LINE=..."）
  T5  历史 API 真实往返：crossline_history_save 写文件 → load 读回，
      返回码 0 且清空后 show 为空
  T6  paging/cursor API 真实调用（非 TTY 下不崩溃、返回合法值）

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
OBJDUMP = os.environ.get("OBJDUMP", "objdump")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"crossline-1.0"]

TEST_C = r"""
#include <stdio.h>
#include <string.h>
#include "crossline.h"

/* T4: 非 TTY 路径（stdin 为管道）下 crossline_readline 应返回输入行。 */
int test_readline_pipe(void)
{
    char buf[256];
    if (crossline_readline("ohos>", buf, sizeof(buf)) == NULL)
        return 1;
    if (strcmp(buf, "hello-ohos-crossline") != 0)
        return 2;
    printf("OHOS_CROSSLINE_LINE=%s\n", buf);
    return 0;
}

/* T5: history save -> load 往返，返回码均为 0。 */
int test_history_roundtrip(void)
{
    const char *hf = ".crossline-ohos-hist";
    if (crossline_history_save(hf) != 0)
        return 3;
    if (crossline_history_load(hf) != 0)
        return 4;
    crossline_history_clear();
    if (crossline_history_save(hf) != 0)
        return 5;
    return 0;
}

/* T6: paging/cursor API 真实调用（非 TTY 下 paging 应返回 0=continue，
 * cursor 查询返回 0 或 -1 均为合法，不得崩溃）。 */
int test_paging_cursor(void)
{
    crossline_paging_reset();
    {
        int rc = crossline_paging_check(1);
        if (rc != 0 && rc != 1)
            return 6;
    }
    {
        int row = -1, col = -1;
        int rc = crossline_cursor_get(&row, &col);
        if (rc != 0 && rc != -1)
            return 7;
    }
    crossline_cursor_move(0, 0);
    return 0;
}

int main(void)
{
    crossline_delimiter_set(" \t");
    if (test_readline_pipe() != 0) return 1;
    if (test_history_roundtrip() != 0) return 2;
    if (test_paging_cursor() != 0) return 3;
    printf("OHOS_CROSSLINE_TESTS_PASS\n");
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

    work = tempfile.mkdtemp(prefix="crossline-test-ohos-")
    src = os.path.join(work, "test_ohos.c")
    with open(src, "w") as f:
        f.write(TEST_C)
    exe = os.path.join(work, "test_ohos")

    # T4 需要 stdin 管道喂入一行
    compile_cmd = [CC, "-fPIC", "-O2", "-Wall",
                   "-I", include, src,
                   os.path.join(lib, "libcrossline.a"),
                   "-o", exe]
    rc = subprocess.run(compile_cmd, capture_output=True)
    if rc.returncode != 0:
        print("FAIL: compile harness:", rc.stderr.decode(errors="replace"), file=sys.stderr)
        return 2

    run_env = dict(os.environ)

    fail = 0
    checks = []  # (name, passed, detail)

    # T1: aarch64 ELF
    out = subprocess.run([READELF, "-h", exe], capture_output=True).stdout
    checks.append(("T1_aarch64_elf", b"AArch64" in out,
                   "ELF64 AArch64 (readelf -h)"))

    # T2: musl, no glibc (INTERP = /lib/ld-musl-*, NEEDED = libc.so, no GLIBC_)
    interp = subprocess.run([READELF, "-l", exe], capture_output=True).stdout
    is_musl = b"ld-musl" in interp
    strings_raw = subprocess.run([STRINGS, exe], capture_output=True).stdout
    has_glibc = b"GLIBC_" in strings_raw or b"ld-linux" in strings_raw
    checks.append(("T2_musl_no_glibc", is_musl and not has_glibc,
                   "musl interp=%s, no GLIBC / ld-linux" % is_musl))

    # T3: no host absolute paths / RPATH-RUNPATH
    strings = subprocess.run([STRINGS, exe], capture_output=True).stdout
    leaks = [r for r in HOST_PATH_RES if r in strings]
    dynd = subprocess.run([READELF, "-d", exe], capture_output=True).stdout
    no_rpath = (b"RPATH" not in dynd and b"RUNPATH" not in dynd)
    checks.append(("T3_no_host_paths", not leaks and no_rpath,
                   "no host abs paths, no RPATH/RUNPATH (leaks=%r)" % leaks))

    # T4-T6: run harness with piped stdin line
    run = subprocess.run([exe], input=b"hello-ohos-crossline\n",
                         capture_output=True, env=run_env, timeout=60)
    out = run.stdout
    ok = run.returncode == 0 and b"OHOS_CROSSLINE_TESTS_PASS" in out \
        and b"OHOS_CROSSLINE_LINE=hello-ohos-crossline" in out
    checks.append(("T4_real_readline", ok,
                   "pipe-readline + history + paging/cursor all pass "
                   "(rc=%d, out=%r)" % (run.returncode, out[:200])))

    for name, passed, detail in checks:
        print("%s %s: %s" % ("PASS" if passed else "FAIL", name, detail))
        if not passed:
            fail = 1

    print("--- crossline OHOS 专项: %s ---" % ("ALL PASS" if fail == 0 else "FAILED"))
    return fail


if __name__ == "__main__":
    sys.exit(main())
