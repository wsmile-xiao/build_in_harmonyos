#!/usr/bin/env python3
"""test_interbench.py — interbench 0.31 安装后消费者测试执行器。

由 test_package/conanfile.py test() 调用，直接执行被测二进制（真实执行器）。
逐例输出 TEST PASS / TEST FAIL，末行输出 TEST SUMMARY，任一例失败 exit(1)。

与 interbench.c 源码对应的关键行为：
  * 运行目录须有 interbench.read，大小恰为 MemTotal kB x 1024，否则首次运行
    会在运行目录实写一份等大文件（真机 32GB 级）。本执行器预创建稀疏文件，
    走 create_read_file() 的"尺寸相符即返回"快路径。
  * loops_per_ms 未知时先校准并写 interbench.loops_per_ms，之后运行直接复用。
  * -h 输出到 stderr，退出码 0；未知 load 名退出码 254（return -2）。
  * 非 root 下 SCHED_FIFO EPERM 属预期：打印 "Results will be unreliable"
    后正常继续，不影响退出码。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

BIN = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "interbench"

PASS_N = 0
FAIL_N = 0


def case(name, ok, detail=""):
    global PASS_N, FAIL_N
    if ok:
        PASS_N += 1
    else:
        FAIL_N += 1
    line = "[TEST] %s ... %s" % (name, "TEST PASS" if ok else "TEST FAIL")
    if detail:
        line += " (%s)" % detail
    print(line, flush=True)


def ram_kb():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                return int(line.split()[1])
    raise RuntimeError("MemTotal not found in /proc/meminfo")


def make_sparse_read_file(workdir):
    # interbench 期望 interbench.read 的大小为 MemTotal kB x 1024 字节；
    # 用稀疏文件满足尺寸检查，避免真写 RAM 大小数据。
    path = os.path.join(workdir, "interbench.read")
    fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o644)
    os.ftruncate(fd, ram_kb() * 1024)
    os.close(fd)
    return path


def run(args, workdir, timeout=300):
    return subprocess.run([BIN] + args, cwd=workdir,
                          capture_output=True, text=True, timeout=timeout)


# ---- cases -----------------------------------------------------------------

def case_help(workdir):
    r = run(["-h"], workdir)
    if r.returncode != 0:
        return False, "rc=%d" % r.returncode
    if "interbench v 0.31 by Con Kolivas" not in r.stderr:
        return False, "version banner missing from stderr"
    if "Show this help" not in r.stderr:
        return False, "help body missing from stderr"
    return True, "rc=0, usage on stderr"


def case_unknown_load(workdir):
    r = run(["-w", "NoSuchLoad"], workdir)
    if r.returncode != 254:
        return False, "rc=%d (expect 254)" % r.returncode
    if 'Unknown load "NoSuchLoad"' not in r.stderr:
        return False, "diagnostic message missing"
    return True, "rc=254, message present"


def case_full_run(workdir):
    # 首次完整基准运行：校准 loops_per_ms + Audio 基准 vs Burn 负载
    make_sparse_read_file(workdir)
    t0 = time.time()
    r = run(["-c", "-t", "10", "-W", "Audio", "-w", "Burn"], workdir)
    dt = time.time() - t0
    problems = []
    if r.returncode != 0:
        problems.append("rc=%d" % r.returncode)
    if "Benchmarking simulated cpu of Audio" not in r.stdout:
        problems.append("Audio benchmark banner missing")
    m = re.search(r"^Burn\s+([0-9.]+)\s*\+/-\s*([0-9.]+)", r.stdout, re.M)
    if not m:
        problems.append("Burn result row missing")
    if "loops_per_ms saved to file" not in r.stderr:
        problems.append("loops_per_ms calibration line missing")
    if "Creating file for read load" in r.stderr:
        problems.append("interbench wrote RAM-sized interbench.read (sparse fast-path not honoured)")
    if dt > 150:
        problems.append("unexpectedly slow: %.1fs" % dt)
    if problems:
        return False, "; ".join(problems)
    return True, "rc=0, latency %sms, %.1fs" % (m.group(1), dt)


def case_rerun_saved_loops(workdir):
    r = run(["-c", "-t", "10", "-W", "Audio", "-w", "Burn"], workdir)
    problems = []
    if r.returncode != 0:
        problems.append("rc=%d" % r.returncode)
    if "loops_per_ms read from file" not in r.stderr:
        problems.append("saved loops_per_ms not reused")
    if "Creating file for read load" in r.stderr:
        problems.append("interbench.read was regenerated")
    if "Benchmarking simulated cpu of Audio" not in r.stdout:
        problems.append("Audio benchmark banner missing")
    if problems:
        return False, "; ".join(problems)
    return True, "rc=0, loops reused"


CASES = [
    ("1/4 help output (-h)", case_help),
    ("2/4 unknown load rejected (-w NoSuchLoad)", case_unknown_load),
    ("3/4 first full run (Audio vs Burn, -t 10, sparse read file)", case_full_run),
    ("4/4 rerun reusing saved loops_per_ms", case_rerun_saved_loops),
]


def main():
    tmp = os.environ.get("TMPDIR") or os.path.join(os.environ.get("HOME", "/storage"), "tmp")
    os.makedirs(tmp, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="interbench-test-", dir=tmp)
    try:
        for name, fn in CASES:
            try:
                ok, detail = fn(workdir)
            except Exception as e:  # noqa: BLE001 - executor must keep running cases
                ok, detail = False, "exception: %r" % e
            case(name, ok, detail)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("TEST SUMMARY: %d passed, %d failed" % (PASS_N, FAIL_N), flush=True)
    sys.exit(1 if FAIL_N else 0)


if __name__ == "__main__":
    main()
