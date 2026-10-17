#!/usr/bin/env python3
"""lldb 0.0.1 R51: 全量 gtest 单测执行器（--gtest_brief=1）
设备适配：find 不在 PATH（shell alias）→ os.walk + stat 可执行位收集；TMPDIR 固定可写路径
"""
import os, re, stat, subprocess, time

B = "/storage/Users/currentUser/tmp/lldb001-build2"
W = "/storage/Users/currentUser/ohpc-contest/lldb-0.0.1/build_in_harmonyos"
OUT = os.path.join(W, ".ohc", "gtest-run")
os.makedirs(OUT, exist_ok=True)
ENV = dict(os.environ, TMPDIR="/storage/Users/currentUser/tmp")

bins = []
for root, dirs, files in os.walk(os.path.join(B, "unittests")):
    for f in files:
        if f.endswith("Tests"):
            pth = os.path.join(root, f)
            try:
                if os.stat(pth).st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    bins.append(pth)
            except OSError:
                pass
bins = sorted(bins)
print(f"发现 {len(bins)} 个测试二进制", flush=True)

total = {"run": 0, "pass": 0, "fail": 0, "skip": 0}
rows = []
for i, b in enumerate(bins, 1):
    name = os.path.relpath(b, B)
    safe = name.replace("/", "_")
    logf = os.path.join(OUT, safe + ".log")
    t0 = time.time()
    crashed = timeout = False
    try:
        with open(logf, "w") as lf:
            p = subprocess.run([b, "--gtest_brief=1"], stdout=lf,
                               stderr=subprocess.STDOUT, timeout=900, env=ENV)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc, timeout = 124, True
    except Exception:
        rc, crashed = 125, True
    dt = time.time() - t0
    txt = open(logf, errors="replace").read() if os.path.exists(logf) else ""
    g = lambda pat: (int(m.group(1)) if (m := re.search(pat, txt)) else None)
    n_run = g(r"\[==========\] (\d+) tests? from")
    n_pass = g(r"\[\s+PASSED\s+\] (\d+) tests?")
    n_fail = g(r"\[\s+FAILED\s+\] (\d+) tests?") or 0
    n_skip = g(r"\[\s+SKIPPED\s+\] (\d+) tests?") or 0
    if n_pass is None and rc == 0 and n_run:
        n_pass = n_run - n_skip
    n_run = n_run or 0; n_pass = n_pass or 0
    total["run"] += n_run; total["pass"] += n_pass
    total["fail"] += n_fail; total["skip"] += n_skip
    flag = " TIMEOUT" if timeout else (" CRASH" if crashed else "")
    line = (f"[{i:02d}/{len(bins)}] {name}: rc={rc} run={n_run} pass={n_pass} "
            f"fail={n_fail} skip={n_skip} {dt:.0f}s{flag}")
    print(line, flush=True)
    rows.append(line)
    rows.append(f"    log: {logf}")

foot = (f"\n=== TOTAL: binaries={len(bins)} run={total['run']} pass={total['pass']} "
        f"fail={total['fail']} skip={total['skip']} ===")
print(foot, flush=True)
with open(os.path.join(OUT, "SUMMARY.txt"), "w") as f:
    f.write("\n".join(rows) + foot + "\n")
