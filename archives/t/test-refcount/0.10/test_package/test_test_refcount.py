#!/usr/bin/env python3
"""test_test_refcount.py — L0c-visible test source for test-refcount 0.10.

R34：真实消费被测包 API，而非空壳。本脚本驱动两个 perl 测试源（各自独立进程，
与上游 t/*.t 的运行模型一致）：

1. `test_test_refcount.pl` —— 正向 API（is_refcount / is_oneref / refcount，
   含 weak ref、循环自引用、各引用类型）；要求 rc=0 且 TAP 全过
2. `test_test_refcount_negative.pl` —— 失败路径：**故意**让被测断言失败
   （非引用入参、引用数不符），故 rc 非 0 是预期；此处核对 STDOUT 的 TAP 中
   确实出现了上游语义要求的诊断文案

Usage: test_test_refcount.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

    与配方 build() 保持一致（hnp perl 5.42.0 的 Errno 导出完整，设备 perl
    5.42.2 缺别名常量）。
    """
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_test_refcount.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块必须在包内
    if not os.path.isfile(os.path.join(site, "Test", "Refcount.pm")):
        raise AssertionError(f"missing packaged module: {site}/Test/Refcount.pm")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    here = os.path.dirname(__file__)

    # ── 1. 正向：要求全过 ────────────────────────────────────────────
    pos = os.path.join(here, "test_test_refcount.pl")
    if not os.path.isfile(pos):
        raise AssertionError(f"test_test_refcount.pl missing: {pos}")
    r = subprocess.run([perl, f"-I{site}", pos], capture_output=True, text=True)
    sys.stdout.write(r.stdout or "")
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"positive consumer test failed (rc={r.returncode})")
    if "not ok" in r.stdout:
        raise SystemExit("FAIL: positive consumer test reported failures")

    # ── 2. 失败路径：故意失败，核对真实诊断文案 ─────────────────────
    neg = os.path.join(here, "test_test_refcount_negative.pl")
    if not os.path.isfile(neg):
        raise AssertionError(f"test_test_refcount_negative.pl missing: {neg}")
    rn = subprocess.run([perl, f"-I{site}", neg], capture_output=True, text=True)
    # TAP 结果行在 stdout，诊断（#   ...）由 Test::Builder 写到 stderr —— 两流都看
    out = (rn.stdout or "") + (rn.stderr or "")
    sys.stdout.write(rn.stdout or "")
    sys.stdout.write(rn.stderr or "")
    expected = [
        "expected a reference, was not given one",
        "expected 1 references, found 2",
    ]
    for frag in expected:
        if frag not in out:
            raise SystemExit(f"FAIL: negative test output missing diagnostic: {frag!r}")
    # 三处故意失败必须真实出现（证明失败路径确实被触发，而非测试未跑到）
    if out.count("not ok") < 3:
        raise SystemExit("FAIL: negative test did not produce the expected failures")

    print("OK: test-refcount 0.10 python-driven consumer check")


if __name__ == "__main__":
    main()
