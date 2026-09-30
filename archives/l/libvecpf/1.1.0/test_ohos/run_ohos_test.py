#!/usr/bin/env python3
"""test_ohos — libvecpf 1.1.0 HarmonyOS PC 平台专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  aarch64 ELF 验证（产物为 ELF64 AArch64）
  T2  musl libc（NEEDED 中无 glibc / ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 /storage/ /home/ /Users/ 与构建目录名）
  T5  真实功能验证：用 OHOS 工具链把消费者程序链接到已安装的 libvecpf.so
      并运行，逐项比对手工独立推算的期望值（覆盖 %vld/%vlx/%vhu/%vd/%vf
      与 vecpf_asprintf），三项回归：大字段宽度不截断、20 万次调用 RSS 不增长、
      4 线程并发一致性。

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

# 宿主/构建机绝对路径特征（鸿蒙 PC 上不应出现）
HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"libvecpf-1.1.0"]


def _find_library(pkg):
    libdir = os.path.join(pkg, "lib")
    for name in sorted(os.listdir(libdir)):
        if name.startswith("libvecpf.so") and not os.path.islink(
                os.path.join(libdir, name)):
            return os.path.join(libdir, name)
    for name in sorted(os.listdir(libdir)):
        if name.startswith("libvecpf.so"):
            return os.path.join(libdir, name)
    raise RuntimeError("libvecpf.so not found under %s" % libdir)


# 消费者程序：只经已安装的公开头文件与共享库调用公开 API。
# 期望值全部由手工按字节布局推算，不由被测实现生成（避免自证）。
CONSUMER_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <vecpf.h>

#define VEC_INT_EXPECTED "287454020 1432778632 -1430532899 -559038737"

static int failures, checks;

static long
rss_kb (void)
{
  FILE *f = fopen ("/proc/self/statm", "r");
  long total = 0, resident = 0;
  if (f == NULL) return -1;
  if (fscanf (f, "%ld %ld", &total, &resident) != 2) { fclose (f); return -1; }
  fclose (f); (void) total;
  return resident * (long) (sysconf (_SC_PAGESIZE) / 1024);
}

static void *
worker (void *arg)
{
  const vp_u_t *u = (const vp_u_t *) arg;
  char local[128];
  int i;
  for (i = 0; i < 20000; i++)
    {
      if (vecpf_sprintf (local, "%vld", u->v) < 0) return (void *) 1;
      if (strcmp (local, VEC_INT_EXPECTED) != 0) return (void *) 1;
    }
  return NULL;
}

static void
check (const char *name, const char *actual, const char *expected)
{
  checks++;
  if (strcmp (actual, expected) != 0)
    { printf ("FAIL %-22s expected \"%s\" got \"%s\"\n", name, expected, actual); failures++; }
  else
    { printf ("ok   %-22s \"%s\"\n", name, actual); }
}

int
main (void)
{
  vp_u_t u;
  char buf[512];
  int n;
  u.ui[0] = 0x11223344u; u.ui[1] = 0x55667788u;
  u.ui[2] = 0xaabbccddu; u.ui[3] = 0xdeadbeefu;

  vecpf_sprintf (buf, "%vld", u.v);
  check ("%vld (4x int32)", buf, "287454020 1432778632 -1430532899 -559038737");
  vecpf_sprintf (buf, "%vlx", u.v);
  check ("%vlx (4x hex32)", buf, "11223344 55667788 aabbccdd deadbeef");
  vecpf_sprintf (buf, "%vhu", u.v);
  check ("%vhu (8x uint16)", buf,
         "13124 4386 30600 21862 52445 43707 48879 57005");
  vecpf_sprintf (buf, "%vd", u.v);
  check ("%vd (16x int8)", buf,
         "68 51 34 17 -120 119 102 85 -35 -52 -69 -86 -17 -66 -83 -34");

  /* 切到单精度通道后 %vf 才有意义（与上游 test_vecpf.c 同一步骤） */
  u.f[0] = 1.5f; u.f[1] = 2.5f; u.f[2] = -3.25f; u.f[3] = 0.0f;
  vecpf_sprintf (buf, "%vf", u.v);
  check ("%vf (4x float)", buf, "1.500000 2.500000 -3.250000 0.000000");

  /* 回到整型通道，供后续 asprintf / 宽度 / 回归用例使用 */
  u.ui[0] = 0x11223344u; u.ui[1] = 0x55667788u;
  u.ui[2] = 0xaabbccddu; u.ui[3] = 0xdeadbeefu;

  {
    char *s = vecpf_asprintf ("[%vlx]", u.v);
    check ("vecpf_asprintf", s ? s : "(null)", "[11223344 55667788 aabbccdd deadbeef]");
    free (s);
  }

  /* 大字段宽度：4 条 lane × 宽 1100 + 3 个分隔空格 = 4403 字符（+NUL = 4404）。
     缓冲按需分配，并做精确长度/边界断言（仅 n>1100 无法发现截断）。 */
  {
    const size_t want = 4 * 1100 + 3;
    char *big = (char *) malloc (want + 8);
    if (big == NULL)
      { printf ("FAIL %-22s could not allocate\n", "wide field"); failures++; checks++; }
    else
      {
        u.ui[0] = 1u; u.ui[1] = 2u; u.ui[2] = 3u; u.ui[3] = 4u;
        n = vecpf_sprintf (big, "%1100vlu", u.v);
        check ("wide field (1100)",
               (n == (int) want && strlen (big) == want && big[0] == ' '
                && big[want - 1] == '4') ? "intact" : "truncated",
               "intact");
        free (big);
      }
    u.ui[0] = 0x11223344u; u.ui[1] = 0x55667788u;
    u.ui[2] = 0xaabbccddu; u.ui[3] = 0xdeadbeefu;
  }

  /* 内存回归：20 万次调用 RSS 不增长 */
  {
    long before = rss_kb ();
    int i, ok = 1;
    if (before < 0) { printf ("skip no-leak (statm unavailable)\n"); }
    else
      {
        for (i = 0; i < 200000 && ok; i++)
          { vecpf_sprintf (buf, "%vld", u.v); if (strcmp (buf, VEC_INT_EXPECTED)) ok = 0; }
        { long g = rss_kb () - before; checks++;
          if (ok && g < 512) printf ("ok   %-22s RSS +%ld kB / 200000 calls\n", "no leak", g);
          else { printf ("FAIL no leak RSS +%ld kB (correct=%d)\n", g, ok); failures++; } }
      }
  }

  /* 并发回归：4 线程共享库不得串状态 */
  {
    pthread_t th[4];
    int i, made = 0, bad = 0;
    for (i = 0; i < 4; i++) if (pthread_create (&th[i], NULL, worker, &u) == 0) made++;
    if (made == 4)
      {
        for (i = 0; i < 4; i++) { void *rc = NULL; pthread_join (th[i], &rc); if (rc) bad++; }
        check ("4-thread concurrency", bad == 0 ? "clean" : "corrupt", "clean");
      }
    else
      { for (i = 0; i < made; i++) pthread_join (th[i], NULL);
        printf ("skip 4-thread concurrency\n"); }
  }

  printf ("OHOS_VECPF_CHECKS=%d FAILURES=%d\n", checks, failures);
  return failures != 0;
}
"""


def main():
    if len(sys.argv) < 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    lib = _find_library(pkg)
    inc = os.path.join(pkg, "include")

    # T1: ELF64 AArch64
    r = subprocess.run([READELF, "-h", lib], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: not ELF64 AArch64", file=sys.stderr)
        return 1
    print("T1 ok: ELF64 AArch64")

    # T2: musl libc（NEEDED 中无 glibc / ld-linux）
    r = subprocess.run([READELF, "-d", lib], capture_output=True)
    if b"GLIBC" in r.stdout or b"ld-linux" in r.stdout:
        print("FAIL: glibc/ld-linux detected", file=sys.stderr)
        return 1
    print("T2 ok: musl (no glibc/ld-linux)")

    # T3: .codesign 段存在（OHOS 签名管线产出）
    r = subprocess.run([READELF, "-S", lib], capture_output=True)
    if b".codesign" not in r.stdout:
        print("FAIL: .codesign section missing", file=sys.stderr)
        return 1
    print("T3 ok: .codesign section present")

    # T4: 无宿主绝对路径泄漏
    st = subprocess.run([STRINGS, lib], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1
    print("T4 ok: no host path leak")

    # T5: 真实功能验证（链接已安装的 .so 并运行）
    tmp = tempfile.mkdtemp(prefix="vecpf-ohos-")
    src = os.path.join(tmp, "consumer.c")
    exe = os.path.join(tmp, "consumer")
    with open(src, "w") as f:
        f.write(CONSUMER_C)
    comp = subprocess.run(
        [CC, "-std=gnu11", "-O2", "-I", inc, src, "-L", os.path.join(pkg, "lib"),
         "-lvecpf", "-Wl,-rpath," + os.path.join(pkg, "lib"), "-lpthread", "-o", exe],
        capture_output=True, text=True)
    if comp.returncode != 0:
        print("FAIL: compile/link failed:\n%s" % comp.stderr, file=sys.stderr)
        return 1
    # 消费者可执行本身也应满足鸿蒙产物身份
    r = subprocess.run([READELF, "-h", exe], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: consumer not ELF64 AArch64", file=sys.stderr)
        return 1
    run = subprocess.run([exe], capture_output=True, text=True)
    sys.stdout.write(run.stdout)
    sys.stderr.write(run.stderr)
    if run.returncode != 0 or "FAILURES=0" not in run.stdout:
        print("FAIL: consumer reported failures (rc=%d)" % run.returncode, file=sys.stderr)
        return 1
    print("T5 ok: real consumer run on OHOS toolchain")
    print("TEST_OHOS_ALL_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
