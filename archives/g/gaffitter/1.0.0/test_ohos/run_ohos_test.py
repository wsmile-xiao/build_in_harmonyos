#!/usr/bin/env python3
"""test_ohos/run_ohos_test.py — gaffitter 鸿蒙专项测试（OHOS aarch64）。

在 OHOS 平台上验证适配产物 bin/fit 的真实平台属性与运行时行为：
  case1: ELF 身份 — ELF64 / AArch64 / PIE（readelf -h）
  case2: musl 动态链接 — INTERP=/lib/ld-musl-aarch64.so.1、NEEDED libc.so、
         OHOS 专属 .note.ohos.ident 段（readelf -lW / -d / -SW）
  case3: 真机运行 — --version 精确版本串 + -h 用法（退出码/输出）
  case4: HMDFS stat 路径 — 创建真实定长文件，fit stat 装箱
         （DiskUsage.cc 的 stat/lstat/readdir 在鸿蒙文件系统上真实工作）
  case5: 真机 GA 组合 — 容量约束（每卷 ≤ target）、容量守恒、理论最优卷数

记录每条断言与命令输出，全部通过后写日志并退出 0。

用法: python3 run_ohos_test.py <fit 二进制绝对路径> [输出日志路径]
"""
import datetime
import os
import re
import subprocess
import sys

BIN = sys.argv[1] if len(sys.argv) > 1 else "fit"
LOG = sys.argv[2] if len(sys.argv) > 2 else "ohos_test.log"

RESULTS = []


def log(text):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    state = "PASS" if cond else "FAIL"
    line = f"[{state}] {name}" + (f" — {detail}" if detail else "")
    log(line)
    print(line)


def run(cmd, cwd=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )


def main():
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("gaffitter OHOS test log\n")
        f.write(f"start: {datetime.datetime.now().isoformat()}\n")
        f.write(f"binary: {os.path.abspath(BIN)}\n")
        f.write(f"host: {os.uname().sysname} {os.uname().machine}\n\n")

    # ---- case1: ELF 身份（ELF64 / AArch64 / PIE）----
    p = run(["readelf", "-h", BIN])
    out = p.stdout.decode("utf-8", "replace")
    check("ELF64 (Class: ELF64)", "ELF64" in out, f"rc={p.returncode}")
    check("AArch64 (Machine: AArch64)", "AArch64" in out)
    check("PIE (Type: DYN Position-Independent)", "DYN (Position-Independent Executable" in out)

    # ---- case2: musl 动态链接属性 ----
    p = run(["readelf", "-lW", BIN])
    out = p.stdout.decode("utf-8", "replace")
    check("musl 解释器 /lib/ld-musl-aarch64.so.1", "Requesting program interpreter: /lib/ld-musl-aarch64.so.1" in out)
    p = run(["readelf", "-d", BIN])
    out = p.stdout.decode("utf-8", "replace")
    check("动态依赖 musl libc.so", "Shared library: [libc.so]" in out)
    p = run(["readelf", "-SW", BIN])
    out = p.stdout.decode("utf-8", "replace")
    check("OHOS 专属 .note.ohos.ident 段", ".note.ohos.ident" in out)

    # ---- case3: 真机运行 ----
    p = run([BIN, "--version"])
    out = p.stdout.decode("utf-8", "replace")
    check("--version 退出码 0", p.returncode == 0, f"rc={p.returncode}")
    check("--version 精确版本串", "gaffitter 1.0.0 (Genetic Algorithm File Fitter) (C) 2005-2015" in out)
    p = run([BIN, "-h"])
    out = p.stdout.decode("utf-8", "replace")
    check("-h 退出码 0", p.returncode == 0, f"rc={p.returncode}")
    check("-h 用法行", "Usage: fit -t target[unit]" in out)

    # ---- case4: HMDFS stat 真实文件装箱 ----
    fix = os.path.join(os.getcwd(), "_fit_ohos_fixtures")
    os.makedirs(fix, exist_ok=True)
    for name, kib in (("f1.bin", 60), ("f2.bin", 30), ("f3.bin", 50)):
        with open(os.path.join(fix, name), "wb") as f:
            f.write(b"\0" * (kib * 1024))
    files = [os.path.join(fix, n) for n in ("f1.bin", "f2.bin", "f3.bin")]
    p = run([BIN, "-t", "100k", "--ss"] + files)
    out = p.stdout.decode("utf-8", "replace")
    check("文件模式退出码 0 (HMDFS stat)", p.returncode == 0, f"rc={p.returncode}")
    check("stat 尺寸 60+30KiB 同卷", "[1] 90.00KiB/100.00KiB of 140.00KiB, Diff: 10.00KiB, Items: 2/3" in out)
    check("剩余 50KiB 单独成卷", "[2] 50.00KiB/100.00KiB of 140.00KiB, Diff: 50.00KiB, Items: 1/3" in out)
    for name in ("f1.bin", "f2.bin", "f3.bin"):
        os.remove(os.path.join(fix, name))
    os.rmdir(fix)

    # ---- case5: 真机 GA 组合语义 ----
    p = run([BIN, "--di", "-t", "100", "60 a", "30 b", "50 c", "20 d"])
    out = p.stdout.decode("utf-8", "replace")
    check("GA 退出码 0", p.returncode == 0, f"rc={p.returncode}")
    sums = [int(m) for m in re.findall(r"^\[\d+\] (\d+)/100 of 160,", out, re.M)]
    check("GA 每卷 ≤ target (容量约束)", len(sums) > 0 and all(s <= 100 for s in sums), f"sums={sums}")
    check("GA 容量守恒 (Σ卷=160)", sum(sums) == 160, f"Σ={sum(sums)}")
    check("GA 卷数=理论最优 2", len(sums) == 2, f"bins={len(sums)}")

    n_pass = sum(1 for _, c in RESULTS if c)
    summary = (
        f"OHOS-TEST {'ALL-PASS' if n_pass == len(RESULTS) else 'FAILED'}: "
        f"{n_pass}/{len(RESULTS)} assertions passed"
    )
    log("\n" + summary)
    print(summary)
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
