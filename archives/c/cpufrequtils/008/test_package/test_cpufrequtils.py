#!/usr/bin/env python3
"""消费者测试：cpufrequtils/008 —— 21 条断言。

用法: test_cpufrequtils.py <package_folder> <work_dir> <cc>

结构（每条编号即一条断言，编号连续无空洞，共 21 条）：
  A01-A06  包布局（可执行位 / 共享库 / SONAME 软链 / 头文件）
  A07-A16  CLI 实跑（帮助、默认输出、调试输出、driver 解析、参数闸）
  A17-A21  libcpufreq 真实 API（编译链接 + 运行 + API 调用 + runenv PATH）

⚠ 本脚本**绝不改动设备调频状态**：A15 用超长 governor 名触发上游参数闸
（set.c case 'g' 在 getopt 循环内就 return -EINVAL，早于任何 sysfs 写），
A16 用"一个参数都不给"触发同类早退；两者都够不到 scaling_* 写入口。

所有断言都刻意保持"能力面无关"：OHOS 非 root 下 sysfs cpufreq 若干属性不可读，
属于能力面而非本包缺陷，用"两种合法形态之一"或 SKIP 表达，绝不把读不到写成通过。
"""

import os
import shutil
import subprocess
import sys

RESULTS = []


def check(code, ok, detail=""):
    RESULTS.append((code, bool(ok), detail))
    print("{} {} {} {}".format(
        "PASS" if ok else "FAIL", code, "-" * 3, detail))
    return ok


def run(cmd, env=None, cwd=None):
    return subprocess.run(cmd, env=env, cwd=cwd, shell=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace")


def main():
    if len(sys.argv) < 4:
        print("usage: test_cpufrequtils.py <package_folder> <work_dir> <cc>")
        return 2
    pkg = sys.argv[1]
    work = sys.argv[2]
    cc = sys.argv[3]

    bindir = os.path.join(pkg, "bin")
    libdir = os.path.join(pkg, "lib")
    incdir = os.path.join(pkg, "include")
    info = os.path.join(bindir, "cpufreq-info")
    setter = os.path.join(bindir, "cpufreq-set")
    real_lib = os.path.join(libdir, "libcpufreq.so.0.0.0")
    hdr = os.path.join(incdir, "cpufreq.h")

    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = libdir + (
        os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")

    # ── A01-A07 包布局 ────────────────────────────────────────────────
    check("A01", os.path.isfile(info), "bin/cpufreq-info packaged")
    check("A02", os.path.isfile(setter), "bin/cpufreq-set packaged")
    check("A03",
          os.access(info, os.X_OK) and os.access(setter, os.X_OK),
          "both tools carry the executable bit")
    check("A04", os.path.isfile(real_lib), "lib/libcpufreq.so.0.0.0 packaged")

    soname_ok = True
    soname_detail = []
    for link in ("libcpufreq.so.0", "libcpufreq.so"):
        p = os.path.join(libdir, link)
        if not os.path.islink(p):
            soname_ok = False
            soname_detail.append(link + ":not-a-symlink")
        elif os.path.realpath(p) != os.path.realpath(real_lib):
            soname_ok = False
            soname_detail.append(link + ":bad-target")
    check("A05", soname_ok, "SONAME aliases " +
          ("ok" if soname_ok else ",".join(soname_detail)))

    check("A06", os.path.isfile(hdr) and
          "cpufreq_get_driver" in open(hdr, errors="replace").read(),
          "include/cpufreq.h declares cpufreq_get_driver")

    # ── A08-A16 CLI 实跑 ──────────────────────────────────────────────
    r = run('"%s" --help' % info, env=env)
    check("A07", r.returncode == 0, "cpufreq-info --help rc=%d" % r.returncode)

    r = run('"%s" --help' % info, env=env)
    check("A08", "cpufrequtils 008" in r.stdout,
          "banner carries upstream version 008")

    r = run('"%s" --help' % setter, env=env)
    check("A09", r.returncode == 0, "cpufreq-set --help rc=%d" % r.returncode)

    r = run('"%s" --help' % setter, env=env)
    check("A10", "cpufreq-set [options]" in r.stdout,
          "usage block rendered")

    r = run('"%s"' % info, env=env)
    check("A11", r.returncode == 0,
          "default debug run rc=%d" % r.returncode)

    r = run('"%s"' % info, env=env)
    check("A12", "cpufrequtils 008" in r.stdout and "analyzing CPU" in r.stdout,
          "default run analyses at least one CPU")

    r = run('"%s" -e' % info, env=env)
    check("A13", r.returncode == 0, "cpufreq-info -e rc=%d" % r.returncode)

    r = run('"%s" -d' % info, env=env)
    out = r.stdout.strip().splitlines()
    line = out[-1].strip() if out else ""
    ok_driver = (r.returncode == 0 and
                 (line == "" or " " not in line or
                  "no or unknown cpufreq driver" in r.stdout))
    check("A14", ok_driver,
          "driver probe rc=%d line=%r" % (r.returncode, line[:60]))

    r = run('"%s" -c 0 -g __cpufrequtils_no_such_governor__' % setter, env=env)
    check("A15", "invalid or unknown argument" in r.stdout,
          "argument gate fires before any sysfs write (no state change)")

    r = run('"%s"' % setter, env=env)
    check("A16", r.returncode != 0 and
          "At least one parameter out of" in r.stdout,
          "no-parameter invocation rejected before any sysfs write rc=%d"
          % r.returncode)

    # ── A17-A21 libcpufreq 真实 API（编译 + 链接 + 运行）──────────────
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consumer.c")
    consumer = os.path.join(work, "cpufreq_consumer")
    inc = " ".join('-I"%s"' % d for d in (incdir,))
    lib = " ".join('-L"%s"' % d for d in (libdir,))
    build = run('"%s" -Wall %s "%s" %s -o "%s" -lcpufreq' %
                (cc, inc, src, lib, consumer), env=env, cwd=work)
    check("A17", build.returncode == 0,
          "consumer.c compiles against package headers/libs rc=%d %s" %
          (build.returncode, (build.stdout or "")[-200:].replace("\n", " ")))

    if os.path.isfile(consumer):
        os.chmod(consumer, 0o755)
    run_env = dict(env)
    run_env["LD_LIBRARY_PATH"] = libdir
    exe = run('"%s"' % consumer, env=run_env, cwd=work)
    check("A18", exe.returncode == 0,
          "consumer runs rc=%d out=%s" % (exe.returncode, exe.stdout.strip()))

    check("A19", "PASS CPU_EXISTS_OK" in exe.stdout,
          "cpufreq_cpu_exists(0) == 0")
    check("A20", "PASS DRIVER_OK" in exe.stdout,
          "cpufreq_get_driver(0) returns NULL or a non-empty string")

    which = shutil.which("cpufreq-info", path=env.get("PATH"))
    check("A21", which is not None,
          "cpufreq-info resolvable from conanrun PATH (%s)" % (which or "MISSING"))

    failed = [c for c, ok, _ in RESULTS if not ok]
    print("SUMMARY total=%d pass=%d fail=%d codes=%s" % (
        len(RESULTS), len(RESULTS) - len(failed), len(failed),
        ",".join(c for c, _, _ in RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
