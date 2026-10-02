#!/usr/bin/env python3
"""R51 upstream test runner — libadwaita 1.8.8 on OHOS (no display).

Runs every upstream test binary with the measured env (see README), 10s
timeout each, records rc + first error line for E471 classification.

Usage:
    python3 run-upstream-tests.py [BUILD_DIR] [OUT_DIR]

  BUILD_DIR  conan 构建根目录（其下含 build-release/tests/ 的测试二进制）。
             缺省 = 本次实测机器的 conan 缓存目录（机位特定，换机器必传参）。
  OUT_DIR    .out / summary.txt 输出目录。缺省 = 本脚本所在目录（入仓台账目录）。

注意：env 在脚本内部固定为本次实测值（GSETTINGS_BACKEND=memory、
GTK_A11Y=none、G_TEST_SRCDIR/G_TEST_BUILDDIR），外部 env 不覆盖之；
找不到测试二进制时以非零码报错退出（不静默空跑）。
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_B = "/storage/Users/currentUser/.conan2/p/b/libad11a423f51f1ac/b"

B = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_B
T = B + "/build-release"
OUT = sys.argv[2] if len(sys.argv) > 2 else HERE
os.makedirs(OUT, exist_ok=True)

env = dict(os.environ)
env["GSETTINGS_BACKEND"] = "memory"
env["GTK_A11Y"] = "none"
# 与本次实测一致（2026-09-28）。63 个测试均在 gtk_init 显示阶段退出
# （SIGTRAP），未到达读取任何资源文件的代码路径，故 G_TEST_SRCDIR /
# G_TEST_BUILDDIR 的取值不影响实测结果，此处保留实测原值。
env["G_TEST_SRCDIR"] = B
env["G_TEST_BUILDDIR"] = T

bins = sorted(f for f in glob.glob(T + "/tests/*")
              if os.path.isfile(f) and os.access(f, os.X_OK))
if not bins:
    sys.stderr.write(
        "error: %s/tests 下无测试二进制——请传 BUILD_DIR 参数"
        "（conan 构建根目录，需以 -Dtests=true 构建）\n" % T)
    sys.exit(1)

summary = open(OUT + "/summary.txt", "w")
passed = failed = 0
for f in bins:
    name = os.path.basename(f)
    try:
        p = subprocess.run([f], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=env, cwd=T, timeout=10)
        rc, data = p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        rc, data = -9, (e.output or b"").decode("utf-8", "replace") + "\n[TIMEOUT 10s]"
    open(OUT + "/" + name + ".out", "w").write(data)
    firsterr = ""
    for line in data.splitlines():
        low = line.lower()
        if any(k in low for k in ("error", "critical", "fail", "cannot",
                                  "could not", "no display", "display")):
            firsterr = line.strip()[:140]
            break
    if rc == 0:
        passed += 1
    else:
        failed += 1
    summary.write("%s rc=%d | %s\n" % (name, rc, firsterr))
    summary.flush()
summary.close()
print("total=%d passed=%d failed=%d" % (len(bins), passed, failed))
